from __future__ import annotations

import heapq
from typing import Optional

from .models import Connection, Graph, Zone, Drone


MOVE_COST = {
    "normal": 1,
    "priority": 1,
    "restricted": 2,
}


class ReservationTable:
    """Track per-turn zone and connection reservations."""

    def __init__(self) -> None:
        """Initialize empty zone and connection reservation tables."""
        #  キー：(zone_name, turn)
        #  値：そのZoneを予約しているドローンIDの集合
        self.zone_reservations: dict[
            tuple[str, int],
            set[str]
        ] = {}

        # キー: (connection_name, turn)
        # 値: そのConnectionを予約しているドローンIDの集合
        self.connection_reservations: dict[
            tuple[str, int],
            set[str]
        ] = {}

    def reserve_zone(
        self,
        zone_name: str,
        turn: int,
        drone_id: str
    ) -> None:
        """Reserve one zone for a drone at a specific turn.

        Args:
            zone_name: Name of the zone to reserve.
            turn: Turn at which the zone is occupied.
            drone_id: Identifier of the reserving drone.
        """
        key = (zone_name, turn)

        if key not in self.zone_reservations:
            self.zone_reservations[key] = set()

        self.zone_reservations[key].add(drone_id)

    def reserve_connection(
            self,
            connection_name: str,
            turn: int,
            drone_id: str
    ) -> None:
        """Reserve one connection for a drone at a specific turn.

        Args:
            connection_name: Canonical connection key.
            turn: Turn at which the connection is occupied.
            drone_id: Identifier of the reserving drone.
        """
        key = (connection_name, turn)

        if key not in self.connection_reservations:
            self.connection_reservations[key] = set()

        self.connection_reservations[key].add(drone_id)

    def zone_is_available(
        self,
        zone: Zone,
        turn: int,
    ) -> bool:
        """Return whether a zone has capacity at a turn.

        Args:
            zone: Zone to inspect.
            turn: Turn to inspect.

        Returns:
            ``True`` if another drone may reserve the zone.
        """
        if zone.max_drones is None:
            return True

        key = (zone.name, turn)

        reserved_drones = self.zone_reservations.get(
            key,
            set()
        )
        return len(reserved_drones) < zone.max_drones

    def connection_is_available(
        self,
        connection: Connection,
        turn: int
    ) -> bool:
        """Return whether a connection has capacity at a turn.

        Args:
            connection: Connection to inspect.
            turn: Turn to inspect.

        Returns:
            ``True`` if another drone may reserve the connection.
        """
        connection_name = self._make_connection_key(connection)
        key = (connection_name, turn)

        reserved_drones = self.connection_reservations.get(
            key,
            set()
        )
        return (
            len(reserved_drones)
            < connection.max_link_capacity
        )

    def _make_connection_key(
        self,
        connection: Connection
    ) -> str:
        """Create an order-independent reservation key.

        Args:
            connection: Connection whose key is requested.

        Returns:
            Endpoint names sorted and joined by a hyphen.
        """
        names = sorted([
            connection.zone1,
            connection.zone2
        ])

        return f"{names[0]}-{names[1]}"

    def reserve_path(
        self,
        graph: Graph,
        path: list[tuple[int, str]],
        drone_id: str
    ) -> None:
        """Reserve every zone and connection used by a path.

        Args:
            graph: Graph used to resolve connections.
            path: Sequence of ``(turn, zone_name)`` route states.
            drone_id: Identifier of the drone owning the path.
        """
        for turn, zone_name in path:
            self.reserve_zone(
                zone_name,
                turn,
                drone_id
            )

        for i in range(len(path) - 1):
            departure_turn, current_zone = path[i]
            arrival_turn, next_zone = path[i + 1]

            if current_zone == next_zone:  # 待機だったら
                continue

            connection = graph.find_connection(
                current_zone,
                next_zone
            )

            connection_key = self._make_connection_key(
                connection
            )

            for turn in range(
                departure_turn + 1,
                arrival_turn + 1
            ):
                self.reserve_connection(
                    connection_key,
                    turn,
                    drone_id
                )

    def connection_is_available_during_move(
        self,
        connection: Connection,
        departure_turn: int,
        arrival_turn: int
    ) -> bool:
        """Check connection capacity throughout a multi-turn movement.

        Args:
            connection: Connection to inspect.
            departure_turn: Turn before the drone enters the connection.
            arrival_turn: Turn at which the drone reaches its destination.

        Returns:
            ``True`` when capacity is available for every movement turn.
        """
        for turn in range(
            departure_turn + 1,
            arrival_turn + 1
        ):
            if not self.connection_is_available(
                connection,
                turn
            ):
                return False

        return True


class PathFinder:
    """Find one drone's earliest route around existing reservations."""

    def __init__(
        self,
        graph: Graph,
        reservations: ReservationTable,
    ) -> None:
        """Initialize a path finder.

        Args:
            graph: Graph to search.
            reservations: Shared reservations from previously planned drones.
        """
        self.graph = graph
        self.reservations = reservations

    def find_path(
        self,
        start: str,
        end: str,
        drone_id: str,
        max_search_turns: int,
        start_turn: int = 0
    ) -> Optional[list[tuple[int, str]]]:
        """Find the earliest capacity-safe route for one drone.

        Args:
            start: Start zone name.
            end: Destination zone name.
            drone_id: Identifier of the drone being planned.
            max_search_turns: Maximum number of turns to explore.
            start_turn: Initial route turn.

        Returns:
            Scheduled route states, or ``None`` if no route is found.
        """
        entry_id = 0

        # (到着ターン, priority評価, 同点比較用ID(TypeError対策), Zone名)
        heap: list[tuple[int, int, int, str]] = [
            (start_turn, 0, entry_id, start)
        ]

        previous: dict[
            tuple[str, int],
            tuple[str, int],
        ] = {}

        expanded: set[tuple[str, int]] = set()

        best_priority: dict[tuple[str, int], int] = {
                    (start, start_turn): 0
        }

        while heap:
            turn, priority_score, _, zone_name = heapq.heappop(heap)
            current_state = (zone_name, turn)

            if current_state in expanded:  # 同じ状態を二度展開しない
                continue

            expanded.add(current_state)

            if zone_name == end:
                return self._reconstruct_path(
                    previous,
                    current_state,
                )

            if turn >= start_turn + max_search_turns:
                continue

            current_zone = self.graph.zones[zone_name]

            #  待機
            wait_turn = turn + 1  # 1ターン待機した状態
            wait_state = (zone_name, wait_turn)

            if self.reservations.zone_is_available(
                    current_zone,
                    wait_turn
            ):
                if not (
                    wait_state in best_priority
                    and best_priority[wait_state] <= priority_score
                ):

                    best_priority[wait_state] = priority_score
                    previous[wait_state] = current_state

                    entry_id += 1
                    heapq.heappush(
                        heap,
                        (
                            wait_turn,
                            priority_score,
                            entry_id,
                            zone_name
                        ),
                    )

            for neighbor_name in self.graph.get_neighbors(
                zone_name
            ):
                neighbor_zone = self.graph.zones[
                    neighbor_name
                ]

                if neighbor_zone.zone_type == "blocked":
                    continue

                move_cost = MOVE_COST[
                    neighbor_zone.zone_type
                ]
                arrival_turn = turn + move_cost

                if neighbor_zone.zone_type == "priority":
                    next_priority_score = priority_score - 1
                else:
                    next_priority_score = priority_score

                # 探索上限を超える到着候補は追加しない
                if (
                    arrival_turn
                    > start_turn + max_search_turns
                ):
                    continue

                connection = self.graph.find_connection(
                    zone_name,
                    neighbor_name
                )

                if not self.reservations.connection_is_available_during_move(
                    connection,
                    turn,
                    arrival_turn
                ):
                    continue

                if not self.reservations.zone_is_available(
                    neighbor_zone,
                    arrival_turn
                ):
                    continue

                next_state = (
                    neighbor_name,
                    arrival_turn
                )

                # 既にnext_stateのpriority_scoreが登録されている場合、値がより良いときだけ更新する
                if (
                    next_state in best_priority
                    and best_priority[next_state] <= next_priority_score
                ):
                    continue

                best_priority[next_state] = next_priority_score
                previous[next_state] = current_state

                entry_id += 1
                heapq.heappush(
                    heap,
                    (
                        arrival_turn,
                        next_priority_score,
                        entry_id,
                        neighbor_name
                    ),
                )

        return None

    def _reconstruct_path(
        self,
        previous: dict[
            tuple[str, int],
            tuple[str, int]
        ],
        goal_state: tuple[str, int]
    ) -> list[tuple[int, str]]:
        """Reconstruct a route from predecessor states.

        Args:
            previous: Mapping from each state to its predecessor.
            goal_state: Final ``(zone_name, turn)`` state.

        Returns:
            Chronological ``(turn, zone_name)`` route states.
        """

        state_path = [goal_state]

        while state_path[-1] in previous:
            state_path.append(
                previous[state_path[-1]]
            )

        state_path.reverse()

        path: list[tuple[int, str]] = []

        for zone_name, turn in state_path:
            path.append((turn, zone_name))

        return path


class MultiDronePathPlanner:
    """Plan multiple drone routes sequentially with shared reservations."""

    def __init__(
        self,
        graph: Graph
    ) -> None:
        """Initialize a planner for a graph.

        Args:
            graph: Graph on which all drone routes are planned.
        """
        self.graph = graph
        self.reservations = ReservationTable()
        self.pathfinder = PathFinder(
            graph,
            self.reservations
        )

    def plan_drone_paths(
        self,
        nb_drones: int
    ) -> list[Drone]:
        """Plan and reserve routes for all requested drones.

        Args:
            nb_drones: Number of drones to create and route.

        Returns:
            Drones containing scheduled paths.

        Raises:
            ValueError: If endpoints are missing or a route cannot be found.
        """
        start_zone_name = self.graph.start_zone_name
        end_zone_name = self.graph.end_zone_name
        if start_zone_name is None or end_zone_name is None:
            raise ValueError("Start and end zones must be configured")

        max_search_turns = self.calculate_max_search_turns(nb_drones)

        drones = []

        for i in range(1, nb_drones + 1):
            drone_id = f"D{i}"

            path = self.pathfinder.find_path(
                start_zone_name,
                end_zone_name,
                drone_id,
                max_search_turns
            )

            if path is None:
                raise ValueError(
                    f"Failed to plan a path for {drone_id}"
                )

            self.reservations.reserve_path(
                self.graph,
                path,
                drone_id
            )

            drones.append(
                Drone(
                    drone_id,
                    path
                )
            )

        return drones

    def calculate_max_search_turns(
        self,
        nb_drones: int
    ) -> int:
        """Calculate a conservative search horizon.

        Args:
            nb_drones: Number of drones being planned.

        Returns:
            Maximum turns explored by each path search.
        """
        return (
            nb_drones
            * len(self.graph.zones)
            * max(MOVE_COST.values())
        )
