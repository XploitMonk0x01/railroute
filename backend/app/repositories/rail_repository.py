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
            Station("HWH", "Howrah Junction", "Kolkata", "West Bengal", 97, True),
            Station("BWN", "Barddhaman Junction", "Bardhaman", "West Bengal", 78, True),
            Station("ASN", "Asansol Junction", "Asansol", "West Bengal", 82, True),
            Station("KIUL", "Kiul Junction", "Lakhisarai", "Bihar", 74, True),
            Station("PNBE", "Patna Junction", "Patna", "Bihar", 94, True),
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
            TrainSegment(
                "12351",
                "Howrah Patna Express",
                "HWH",
                "PNBE",
                time(22, 0),
                time(6, 0),
                480,
                532,
                900,
                "3A",
                0,
                daily,
            ),
            TrainSegment(
                "13005",
                "Howrah Amritsar Mail",
                "HWH",
                "BWN",
                time(8, 0),
                time(9, 15),
                75,
                95,
                160,
                "3A",
                18,
                daily,
            ),
            TrainSegment(
                "12333",
                "Vibhuti Express",
                "BWN",
                "PNBE",
                time(10, 5),
                time(16, 40),
                395,
                437,
                620,
                "3A",
                12,
                daily,
            ),
            TrainSegment(
                "12321",
                "Mumbai Mail via Asansol",
                "HWH",
                "ASN",
                time(7, 20),
                time(10, 5),
                165,
                200,
                260,
                "3A",
                7,
                daily,
            ),
            TrainSegment(
                "13287",
                "South Bihar Express",
                "ASN",
                "PNBE",
                time(11, 15),
                time(17, 55),
                400,
                332,
                590,
                "3A",
                20,
                daily,
            ),
            TrainSegment(
                "13029",
                "Mokama Passenger Link",
                "HWH",
                "KIUL",
                time(6, 30),
                time(14, 20),
                470,
                414,
                510,
                "SL",
                42,
                daily,
            ),
            TrainSegment(
                "13235",
                "Danapur Intercity",
                "KIUL",
                "PNBE",
                time(15, 10),
                time(18, 15),
                185,
                118,
                170,
                "SL",
                36,
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
