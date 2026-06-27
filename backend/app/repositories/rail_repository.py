from abc import ABC, abstractmethod
from datetime import time

from app.models.rail import Station, TrainSegment


class RailRepository(ABC):
    @abstractmethod
    def list_stations(self) -> list[Station]:
        raise NotImplementedError

    @abstractmethod
    def search_stations(self, query: str) -> list[Station]:
        raise NotImplementedError

    @abstractmethod
    def list_segments_from(self, station_code: str) -> list[TrainSegment]:
        raise NotImplementedError

    @abstractmethod
    def list_direct_segments(self, source_code: str, destination_code: str) -> list[TrainSegment]:
        raise NotImplementedError

    @abstractmethod
    def list_all_segments(self) -> list[TrainSegment]:
        raise NotImplementedError


class InMemoryRailRepository(RailRepository):
    def __init__(self) -> None:
        self._stations = [
            Station("ADI", "Ahmedabad Junction", "Ahmedabad", "Gujarat", 91, True),
            Station("BRC", "Vadodara Junction", "Vadodara", "Gujarat", 85, True),
            Station("KOTA", "Kota Junction", "Kota", "Rajasthan", 88, True),
            Station("JP", "Jaipur Junction", "Jaipur", "Rajasthan", 83, True),
            Station("NDLS", "New Delhi", "New Delhi", "Delhi", 98, True),
        ]
        daily = frozenset(range(7))
        self._segments = [
            TrainSegment(
                "12957",
                "Swarna Jayanti Rajdhani",
                "ADI",
                "NDLS",
                time(17, 40),
                time(7, 30),
                830,
                934,
                1850,
                "3A",
                0,
                daily,
            ),
            TrainSegment(
                "12959",
                "Intercity Superfast",
                "ADI",
                "BRC",
                time(8, 0),
                time(9, 45),
                105,
                100,
                160,
                "CC",
                18,
                daily,
            ),
            TrainSegment(
                "12903",
                "Golden Temple Mail",
                "BRC",
                "KOTA",
                time(10, 30),
                time(16, 10),
                340,
                430,
                520,
                "3A",
                12,
                daily,
            ),
            TrainSegment(
                "12059",
                "Kota Jan Shatabdi",
                "KOTA",
                "NDLS",
                time(17, 10),
                time(23, 20),
                370,
                465,
                640,
                "CC",
                21,
                daily,
            ),
            TrainSegment(
                "12967",
                "Jaipur Superfast",
                "ADI",
                "JP",
                time(19, 55),
                time(5, 10),
                555,
                625,
                550,
                "3A",
                9,
                daily,
            ),
            TrainSegment(
                "12015",
                "Ajmer Shatabdi",
                "JP",
                "NDLS",
                time(6, 5),
                time(10, 40),
                275,
                310,
                300,
                "CC",
                34,
                daily,
            ),
        ]

    def list_stations(self) -> list[Station]:
        return sorted(self._stations, key=lambda station: station.score, reverse=True)

    def search_stations(self, query: str) -> list[Station]:
        normalized = query.strip().lower()
        if not normalized:
            return self.list_stations()[:10]
        matches = [
            station
            for station in self._stations
            if normalized in station.code.lower()
            or normalized in station.name.lower()
            or normalized in station.city.lower()
        ]
        return sorted(matches, key=lambda station: station.score, reverse=True)

    def list_segments_from(self, station_code: str) -> list[TrainSegment]:
        normalized = station_code.upper()
        return [segment for segment in self._segments if segment.from_station == normalized]

    def list_direct_segments(self, source_code: str, destination_code: str) -> list[TrainSegment]:
        source = source_code.upper()
        destination = destination_code.upper()
        return [
            segment
            for segment in self._segments
            if segment.from_station == source and segment.to_station == destination
        ]

    def list_all_segments(self) -> list[TrainSegment]:
        return self._segments
