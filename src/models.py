from __future__ import annotations
from typing import Optional

from .terminal import colorize


class Zone:
    def __init__(
            self,
            name: str,
            x: int,
            y: int,
            zone_type: str = "normal",
            max_drones: Optional[int] = 1,
            color: Optional[str] = None
    ) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.zone_type = zone_type
        self.max_drones = max_drones
        self.color = color
        self.occupants: set[str] = set()  # 今ここにいるドローンのID

    def has_capacity(self) -> bool:
        if self.max_drones is None:
            return True
        return len(self.occupants) < self.max_drones

    def display_name(self) -> str:
        return colorize(self.name, self.color)


class Connection:
    def __init__(
            self,
            zone1: str,
            zone2: str,
            max_link_capacity: int = 1,
            has_explicit_capacity: bool = False,
    ) -> None:
        self.zone1 = zone1
        self.zone2 = zone2
        self.max_link_capacity = max_link_capacity
        self.has_explicit_capacity = has_explicit_capacity
        self.travelers: set[str] = set()  # 今この橋を渡っているドローンのID

    def other_side(self, zone_name: str) -> str:
        if zone_name == self.zone1:
            return self.zone2
        return self.zone1

    def has_capacity(self) -> bool:
        return len(self.travelers) < self.max_link_capacity

    def display_name(self, graph: "Graph") -> str:
        """両端の Zone に表示方法を委譲して、色付き接続名を返す。"""
        return (
            f"{graph.zones[self.zone1].display_name()}"
            f"-{graph.zones[self.zone2].display_name()}"
        )


class Graph:
    def __init__(self) -> None:
        self.zones: dict[str, Zone] = {}
        self.connections: list[Connection] = []
        self.start_zone_name: Optional[str] = None
        self.end_zone_name: Optional[str] = None

    def add_zone(
            self,
            zone: Zone,
            is_start: bool = False,
            is_end: bool = False
    ) -> None:
        self.zones[zone.name] = zone
        if is_start:
            self.start_zone_name = zone.name
        if is_end:
            self.end_zone_name = zone.name

    def add_connection(self, connection: Connection) -> None:
        self.connections.append(connection)

    def get_neighbors(self, zone_name: str) -> list[str]:
        neighbors = []

        for connection in self.connections:
            if connection.zone1 == zone_name or connection.zone2 == zone_name:
                neighbors.append(connection.other_side(zone_name))
        return neighbors

    def find_connection(self, zone_a: str, zone_b: str) -> Connection:
        for connection in self.connections:
            if {connection.zone1, connection.zone2} == {zone_a, zone_b}:
                return connection
        raise ValueError(f"Not found connection to {zone_a} and {zone_b}")


class Drone:
    def __init__(
            self,
            drone_id: str,
            path: list[tuple[int, str]]
    ) -> None:
        self.id = drone_id
        self.path = path
        self.path_index = 0  # 今pathの何番目にいるか
        self.delivered = False
        # 移動中の時にだけ使う情報
        self.transit_connection: Optional[Connection] = None
