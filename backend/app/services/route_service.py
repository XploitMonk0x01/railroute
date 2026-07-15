import heapq
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone

from app.core.config import settings
from app.core.graph import rail_graph
from app.models.rail import TrainSegment
from app.repositories.rail_repository import RailRepository
from app.services.scraper_integration import scrape_and_upsert_live, RouteQuery
from app.schemas.search import (
    FilterPreset,
    RouteResponse,
    RouteSegmentResponse,
    SearchRequest,
    SearchResponse,
)


DEFAULT_WEIGHTS = {
    "time": 0.40,
    "fare": 0.25,
    "transfer": 0.20,
    "wait": 0.10,
    "availability": 0.0,
}

FILTER_PRESETS = {
    "default": DEFAULT_WEIGHTS,
    "fastest": {"time": 0.80, "fare": 0.05, "transfer": 0.10, "wait": 0.05, "availability": 0.0},
    "cheapest": {"time": 0.10, "fare": 0.75, "transfer": 0.10, "wait": 0.05, "availability": 0.0},
    "least_transfers": {"time": 0.20, "fare": 0.20, "transfer": 0.55, "wait": 0.05, "availability": 0.0},
    "best_availability": {"time": 0.25, "fare": 0.15, "transfer": 0.15, "wait": 0.05, "availability": -0.40},
}

NORMALIZERS = {
    "time": 1440,
    "fare": 3000,
    "wait": 240,
}


@dataclass(order=True)
class RouteState:
    cost: float
    station_code: str = field(compare=False)
    current_time: datetime = field(compare=False)
    path: list[tuple[TrainSegment, datetime, datetime, int]] = field(compare=False, default_factory=list)
    visited_stations: frozenset[str] = field(compare=False, default_factory=frozenset)
    total_fare: float = field(compare=False, default=0)
    transfers: int = field(compare=False, default=0)
    wait_min: int = field(compare=False, default=0)


class RouteService:
    """
    Core business service for discovering and ranking train routes.
    Utilizes an in-memory NetworkX graph to efficiently find direct and multi-hop paths.
    Integrates with the Playwright scraper to fetch real-time availability on the fly.
    """

    def __init__(self, rail_repository: RailRepository) -> None:
        self._rail_repository = rail_repository
        if rail_graph.G.number_of_edges() == 0:
            rail_graph.build(
                self._rail_repository.list_stations(),
                self._rail_repository.list_all_segments(),
            )

    async def search(self, request: SearchRequest) -> SearchResponse:
        if request.source == request.destination:
            raise ValueError("source and destination must be different")

        # 1. Find candidate routes IGNORING availability
        candidates = self._find_routes(request, ignore_availability=True)
        direct_cand = self._direct_segment(request, ignore_availability=True)
        
        # 2. Collect unique queries to scrape
        queries_to_scrape = {}

        # ALWAYS scrape the direct user-requested route — this ensures Chromium
        # launches even when the route is not yet in the static seeded graph.
        direct_user_query = RouteQuery(
            from_code=request.source,
            to_code=request.destination,
            date=request.date,
            class_code=request.class_code or "3A",
        )
        queries_to_scrape[str(direct_user_query)] = direct_user_query

        if direct_cand:
            q = RouteQuery(
                from_code=direct_cand.from_station,
                to_code=direct_cand.to_station,
                date=request.date,
                class_code=request.class_code or "3A",
            )
            queries_to_scrape[str(q)] = q

        # To avoid DDOSing the provider and timing out, only scrape up to 3 candidate segments
        # from the shortest paths, and rely on DB cache for the rest.
        count = 0
        for state in candidates:
            if count >= 3:
                break
            for path_segment in state.path:
                seg = path_segment[0]
                q = RouteQuery(
                    from_code=seg.from_station,
                    to_code=seg.to_station,
                    date=request.date,
                    class_code=request.class_code or "3A",
                )
                if str(q) not in queries_to_scrape:
                    queries_to_scrape[str(q)] = q
                    count += 1
                if count >= 3:
                    break

        # 3. Live Scrape (always at least one query — the direct user request)
        await scrape_and_upsert_live(list(queries_to_scrape.values()))
        
        # 4. Refresh Graph Data (since db was updated, we can just fetch real availability)
        # However, for simplicity and since _find_routes uses in-memory rail_graph (which we can update)
        # or we could just re-instantiate or we can just fetch from DB again?
        # Wait, the graph engine (rail_graph.G) uses in-memory edge data.
        # It's NOT automatically updated when we write to DB!
        # We need to update the in-memory graph edges with the new availability.
        # Or we can just re-read the segments from the DB and rebuild the graph.
        
        stations = self._rail_repository.list_stations()
        segments = self._rail_repository.list_all_segments()
        rail_graph.build(stations, segments)

        # 5. Now find routes ENFORCING availability
        routes = self._find_routes(request, ignore_availability=False)
        direct_segment = self._direct_segment(request, ignore_availability=False)
        
        alternatives = [
            route
            for route in routes
            if route.transfers > 0 or not self._is_direct_path(route, request)
        ]
        ranked_alternatives = self._rank_routes(alternatives, request.filter_preset)

        return SearchResponse(
            direct_available=bool(direct_segment and direct_segment.available_seats > 0),
            direct_train=self._segment_response(
                (
                    direct_segment,
                    datetime.combine(request.date, direct_segment.departure),
                    datetime.combine(request.date, direct_segment.departure) + timedelta(minutes=direct_segment.duration_min),
                    0,
                )
            )
            if direct_segment
            else None,
            alternatives=[
                self._route_response(route, index, request.filter_preset)
                for index, route in enumerate(ranked_alternatives, start=1)
            ],
            generated_at=datetime.now(timezone.utc),
        )

    def _find_routes(self, request: SearchRequest, ignore_availability: bool = False) -> list[RouteState]:
        start_time = datetime.combine(request.date, time.min)
        heap = [RouteState(0, request.source, start_time, visited_stations=frozenset({request.source}))]
        visited: dict[tuple[str, int], float] = {}
        results: list[RouteState] = []
        max_budget = request.constraints.max_budget or float("inf")

        while heap and len(results) < settings.default_top_k_routes:
            state = heapq.heappop(heap)
            if state.station_code == request.destination:
                results.append(state)
                continue

            visit_key = (state.station_code, state.transfers)
            if visited.get(visit_key, float("inf")) <= state.cost:
                continue
            visited[visit_key] = state.cost

            for _, next_station, edge_data in rail_graph.G.edges(state.station_code, data=True):
                segment = TrainSegment(
                    train_number=edge_data["train_number"],
                    train_name=edge_data["train_name"],
                    from_station=state.station_code,
                    to_station=next_station,
                    departure=edge_data["departure"],
                    arrival=edge_data["arrival"],
                    duration_min=edge_data["duration_min"],
                    distance_km=edge_data["distance_km"],
                    fare=edge_data["fare"],
                    class_code=edge_data["class_code"],
                    available_seats=edge_data["available_seats"],
                    run_days=frozenset(edge_data["run_days"]),
                )
                if segment.to_station in state.visited_stations:
                    continue
                if not segment.runs_on(request.date):
                    continue
                if request.class_code and segment.class_code != request.class_code:
                    continue
                if not ignore_availability and segment.available_seats <= 0 and segment.to_station == request.destination:
                    continue

                last_train = state.path[-1][0].train_number if state.path else None
                is_transfer = bool(last_train and last_train != segment.train_number)
                transfers = state.transfers + int(is_transfer)
                if transfers > request.constraints.max_transfers:
                    continue

                departure = self._next_departure(state.current_time, segment.departure)
                arrival = departure + timedelta(minutes=segment.duration_min)
                wait_min = int((departure - state.current_time).total_seconds() // 60)
                effective_wait_min = wait_min if state.path else 0
                if effective_wait_min > request.constraints.max_wait_min:
                    continue

                total_fare = state.total_fare + segment.fare
                if total_fare > max_budget:
                    continue

                penalty = settings.transfer_penalty_min if is_transfer else 0
                next_state = RouteState(
                    cost=state.cost + segment.duration_min + wait_min + penalty,
                    station_code=segment.to_station,
                    current_time=arrival,
                    path=state.path + [(segment, departure, arrival, effective_wait_min)],
                    visited_stations=state.visited_stations | {segment.to_station},
                    total_fare=total_fare,
                    transfers=transfers,
                    wait_min=state.wait_min + effective_wait_min,
                )
                heapq.heappush(heap, next_state)

        return results

    def _direct_segment(self, request: SearchRequest, ignore_availability: bool = False) -> TrainSegment | None:
        candidates = [
            segment
            for segment in self._rail_repository.list_direct_segments(request.source, request.destination)
            if segment.runs_on(request.date)
            and (request.class_code is None or segment.class_code == request.class_code)
        ]
        if ignore_availability:
            return min(candidates, key=lambda segment: segment.duration_min, default=None)
        else:
            return min(candidates, key=lambda segment: (segment.available_seats <= 0, segment.duration_min), default=None)

    def _is_direct_path(self, route: RouteState, request: SearchRequest) -> bool:
        return (
            len(route.path) == 1
            and route.path[0][0].from_station == request.source
            and route.path[0][0].to_station == request.destination
        )

    def _rank_routes(self, routes: list[RouteState], preset: FilterPreset) -> list[RouteState]:
        return sorted(routes, key=lambda route: self._score(route, preset))

    def _score(self, route: RouteState, preset: FilterPreset) -> float:
        weights = FILTER_PRESETS[preset]
        travel_time = sum(segment.duration_min for segment, *_ in route.path)
        average_availability = sum(segment.available_seats for segment, *_ in route.path) / len(route.path)
        score = (
            (travel_time / NORMALIZERS["time"]) * weights["time"]
            + (float(route.total_fare) / NORMALIZERS["fare"]) * weights["fare"]
            + route.transfers * weights["transfer"]
            + (route.wait_min / NORMALIZERS["wait"]) * weights["wait"]
            + min(average_availability / 100, 1) * weights["availability"]
        )
        return round(score, 4)

    def _route_response(self, route: RouteState, index: int, preset: FilterPreset) -> RouteResponse:
        segments_out = []
        last_train: str | None = None
        day = 1
        for i, path_segment in enumerate(route.path):
            seg = path_segment[0]
            is_transfer = bool(last_train and last_train != seg.train_number)
            segments_out.append(self._segment_response(path_segment, is_transfer=is_transfer, day=day))
            last_train = seg.train_number
        return RouteResponse(
            route_id=f"r_{index:03}",
            score=self._score(route, preset),
            total_time_min=sum(segment.duration_min for segment, *_ in route.path),
            total_fare=route.total_fare,
            transfer_count=route.transfers,
            wait_min=route.wait_min,
            segments=segments_out,
        )

    def _segment_response(
        self,
        path_segment: tuple[TrainSegment, datetime, datetime, int],
        *,
        is_transfer: bool = False,
        day: int = 1,
    ) -> RouteSegmentResponse:
        segment, departure, arrival, wait_min = path_segment
        return RouteSegmentResponse(
            train_number=segment.train_number,
            train_name=segment.train_name,
            **{
                "from": segment.from_station,
                "to": segment.to_station,
                "class": segment.class_code,
            },
            departure=departure.time(),
            arrival=arrival.time(),
            duration_min=segment.duration_min,
            distance_km=segment.distance_km,
            wait_min=wait_min,
            is_transfer=is_transfer,
            day=day,
            fare=segment.fare,
            availability=f"AVAILABLE ({segment.available_seats})" if segment.available_seats > 0 else "WL",
        )

    def _next_departure(self, current_time: datetime, departure_time: time) -> datetime:
        departure = datetime.combine(current_time.date(), departure_time)
        if departure < current_time:
            departure += timedelta(days=1)
        return departure
