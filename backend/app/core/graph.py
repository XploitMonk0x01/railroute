import networkx as nx
from typing import List
from datetime import time

class RailGraph:
    def __init__(self):
        # MultiDiGraph: directed, multiple edges allowed
        self.G = nx.MultiDiGraph()

    def build(self, stations: List, segments: List):
        self.G.clear()
        
        # Add station nodes
        for s in stations:
            self.G.add_node(
                s.code,
                name=s.name,
                score=s.score,
                is_junction=s.is_junction
            )

        # Add directed edges for segments
        for seg in segments:
            self.G.add_edge(
                seg.from_station,
                seg.to_station,
                train_number=seg.train_number,
                train_name=seg.train_name,
                departure=seg.departure,
                arrival=seg.arrival,
                duration_min=seg.duration_min,
                distance_km=seg.distance_km,
                fare=seg.fare,
                class_code=seg.class_code,
                available_seats=seg.available_seats,
                run_days=seg.run_days
            )

# Global singleton instance
rail_graph = RailGraph()
