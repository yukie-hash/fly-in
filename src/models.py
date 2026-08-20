from __future__ import annotations
from typing import Optional


class Zone:
    """Represent a graph zone and the drones currently occupying it."""

    def __init__(
            self,
            name: str,
            x: int,
            y: int,
            zone_type: str = "normal",
            max_drones: Optional[int] = 1,
            color: Optional[str] = None
    ) -> None:
        """Initialize a zone.

        Args:
            name: Unique zone name.
            x: Horizontal map coordinate.
            y: Vertical map coordinate.
            zone_type: Movement behavior assigned to the zone.
            max_drones: Maximum occupants, or ``None`` for no limit.
            color: Optional terminal color name.
        """
        self.name = name
        self.x = x
        self.y = y
        self.zone_type = zone_type
        self.max_drones = max_drones
        self.color = color
        self.occupants: set[str] = set()  # 今ここにいるドローンのID

    def has_capacity(self) -> bool:
        """Return whether another drone can enter the zone."""
        if self.max_drones is None:
            return True
        return len(self.occupants) < self.max_drones


class Connection:
    """Represent a bidirectional connection between two zones."""

    def __init__(
            self,
            zone1: str,
            zone2: str,
            max_link_capacity: int = 1,
            has_explicit_capacity: bool = False,
    ) -> None:
        """Initialize a connection.

        Args:
            zone1: Name of the first endpoint.
            zone2: Name of the second endpoint.
            max_link_capacity: Maximum simultaneous travelers.
            has_explicit_capacity: Whether the map specified the capacity.
        """
        self.zone1 = zone1
        self.zone2 = zone2
        self.max_link_capacity = max_link_capacity
        self.has_explicit_capacity = has_explicit_capacity
        self.travelers: set[str] = set()  # 今この橋を渡っているドローンのID

    def other_side(self, zone_name: str) -> str:
        """Return the endpoint opposite ``zone_name``.

        Args:
            zone_name: Name of one endpoint.

        Returns:
            Name of the other endpoint.
        """
        if zone_name == self.zone1:
            return self.zone2
        return self.zone1

    def has_capacity(self) -> bool:
        """Return whether another drone can enter the connection."""
        return len(self.travelers) < self.max_link_capacity


class Graph:
    """Store zones, connections, and the designated endpoint names."""

    def __init__(self) -> None:
        """Initialize an empty graph."""
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
        """Add a zone and optionally designate it as an endpoint.

        Args:
            zone: Zone to add.
            is_start: Whether the zone is the start hub.
            is_end: Whether the zone is the end hub.
        """
        self.zones[zone.name] = zone
        if is_start:
            self.start_zone_name = zone.name
        if is_end:
            self.end_zone_name = zone.name

    def add_connection(self, connection: Connection) -> None:
        """Add a bidirectional connection to the graph.

        Args:
            connection: Connection to add.
        """
        self.connections.append(connection)

    def get_neighbors(self, zone_name: str) -> list[str]:
        """Return names of zones directly connected to a zone.

        Args:
            zone_name: Zone whose neighbors are requested.

        Returns:
            Connected zone names in connection insertion order.
        """
        neighbors = []

        for connection in self.connections:
            if connection.zone1 == zone_name or connection.zone2 == zone_name:
                neighbors.append(connection.other_side(zone_name))
        return neighbors

    def find_connection(self, zone_a: str, zone_b: str) -> Connection:
        """Find the connection joining two zones.

        Args:
            zone_a: Name of one endpoint.
            zone_b: Name of the other endpoint.

        Returns:
            Matching connection.

        Raises:
            ValueError: If no matching connection exists.
        """
        for connection in self.connections:
            if {connection.zone1, connection.zone2} == {zone_a, zone_b}:
                return connection
        raise ValueError(f"Not found connection to {zone_a} and {zone_b}")


class Drone:
    """Track a drone's planned route and simulation state."""

    def __init__(
            self,
            drone_id: str,
            path: list[tuple[int, str]]
    ) -> None:
        """Initialize a drone.

        Args:
            drone_id: Unique drone identifier.
            path: Sequence of ``(turn, zone_name)`` route states.
        """
        self.id = drone_id
        self.path = path
        self.path_index = 0  # 今pathの何番目にいるか
        self.delivered = False
        # 移動中の時にだけ使う情報
        self.transit_connection: Optional[Connection] = None
