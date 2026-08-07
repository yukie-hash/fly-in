from __future__ import annotations
import sys

import heapq
from typing import Optional

from .visualize import TerminalRenderer


MOVE_COST = {
    "normal": 1,
    "priority": 1,
    "restricted": 2,
}


COLOR_CODES = {
    "black": "\033[30m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "blue": "\033[94m",
    "gray": "\033[90m",
    "white": "\033[97m",
    "cyan": "\033[96m",
    "purple": "\033[95m",
    "violet": "\033[38;5;141m",
    "crimson": "\033[38;5;197m",
    "lime": "\033[92m",
    "orange": "\033[38;5;208m",
    "brown": "\033[38;5;130m",
    "maroon": "\033[38;5;52m",
    "darkred": "\033[38;5;88m",
    "gold": "\033[38;5;220m",
}
RESET_CODE = "\033[0m"
RAINBOW_CODES = (
    "\033[91m",  # red
    "\033[93m",  # yellow
    "\033[92m",  # green
    "\033[96m",  # cyan
    "\033[94m",  # blue
    "\033[95m",  # purple
)
 

def colorize(text: str, color_name: Optional[str]) -> str:
    if color_name == "rainbow":
        return "".join(
            f"{RAINBOW_CODES[index % len(RAINBOW_CODES)]}{character}"
            for index, character in enumerate(text)
        ) + RESET_CODE
    if color_name is None or color_name not in COLOR_CODES:
        return text
    return f"{COLOR_CODES[color_name]}{text}{RESET_CODE}"


class Zone:
    def __init__(
            self,
            name:str,
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
    
    def find_connection(self, zone_a :str, zone_b: str) -> Connection:
        for connection in self.connections:
            if {connection.zone1, connection.zone2} == {zone_a, zone_b}:
                return connection
        raise ValueError(f"Not found connection to {zone_a} and {zone_b}")


def extract_metadata(rest: str) -> dict[str, str]:
    if "[" not in rest:
        return {}
    
    metadata_str = rest.split("[")[1].split("]")[0]
    metadata = {}
    for token in metadata_str.split():
        key, value = token.split("=")
        metadata[key] = value
    return metadata


def build_graph_from_map(filepath: str) -> tuple[int, Graph]:
    graph = Graph()
    nb_drones: Optional[int] = None

    with open(filepath, encoding="utf-8") as file:
        lines = file.readlines()

    for raw_line in lines:
        line = raw_line.split("#")[0].strip()
        if not line:
            continue

        if line.startswith("nb_drones:"):
            nb_drones = int(line.split(":")[1].strip())
        
        elif line.startswith(("start_hub:", "end_hub:", "hub:")):
            is_start = line.startswith("start_hub:")
            is_end = line.startswith("end_hub:")
            rest = line.split(":", 1)[1].strip()
            fields = rest.split()
            name = fields[0]
            x = int(fields[1])
            y = int(fields[2])
            metadata = extract_metadata(rest)
            zone_type = metadata.get("zone", "normal")
            color = metadata.get("color")

            if is_start or is_end:
                max_drones = None
            else:
                max_drones = int(metadata.get("max_drones", "1"))

            zone = Zone(name, x, y, zone_type, max_drones, color)
            graph.add_zone(zone, is_start=is_start, is_end=is_end)
        
        elif line.startswith("connection:"):
            rest = line.split(":", 1)[1].strip()
            metadata = extract_metadata(rest)

            main_part = rest.split("[")[0].strip()
            zone1, zone2 = main_part.split("-")

            max_link_capacity = int(metadata.get("max_link_capacity", "1"))

            graph.add_connection(
                Connection(
                    zone1,
                    zone2,
                    max_link_capacity,
                    has_explicit_capacity="max_link_capacity" in metadata,
                )
            )

    if nb_drones is None:
        raise ValueError(
            "Not found nb_drones in the map"
        )

    if graph.start_zone_name is None:
        raise ValueError(
            "Not found start_hub in the map"
        )

    if graph.end_zone_name is None:
            raise ValueError(
                "Not found end_hub in the map"
            )

    return nb_drones, graph


class ReservationTable:
    def __init__(self) -> None:
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
        """指定ターンのZoneを予約する

        Args:
            zone_name (str): _description_
            turn (int): _description_
            drone_id (str): _description_
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
        """指定ターンのConnectionを予約する

        Args:
            connection_name (str): _description_
            turn (int): _description_
            drone_id (str): _description_
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
        """指定ターンのZoneに空きがあるか確認する

        Args:
            zone (Zone): _description_
            turn (int): _description_

        Returns:
            bool: _description_
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
        """指定ターンのConnectionに空きがあるか確認する

        Args:
            connection (Connection): _description_
            turn (int): _description_

        Returns:
            bool: _description_
        """
        connection_name = self._connection_name(connection)
        key = (connection_name, turn)

        reserved_drones = self.connection_reservations.get(
            key,
            set()
        )
        return (
            len(reserved_drones)
            < connection.max_link_capacity
        )

    def _connection_name(
        self,
        connection: Connection
    ) -> str:
        """Connectionを予約表用の文字列に変換する。"""
        names = sorted([
            connection.zone1,
            connection.zone2
        ])

        return f"{names[0]}-{names[1]}"

class PathFinder:
    """予約表を考慮して、1台分の最短到着経路を探す
    """
    def __init__(
        self,
        graph: Graph,
        reservations: ReservationTable,
        max_horizon: int = 200
    ) -> None:
        self.graph = graph
        self.reservations = reservations
        self.max_horizen = max_horizon

    def find_path(
        self,
        start: str,
        end: str,
        drone_id: str,
        start_turn: int = 0
    ) -> Optional[list[tuple[int, str]]]:

        entry_id = 0

        # (到着ターン, priority評価, 同点比較用ID(TypeError対策), Zone名)
        heap: list[tuple[int, int, str]] = [
            (start_turn, 0, entry_id, start)
        ]

        previous: dict[
            tuple[str, int],
            tuple[str, int],
        ] = {}

        visited: set[tuple[str, int]] = set()

        while heap:
            turn, priority_score, _, zone_name = heapq.heappop(heap)
            current_state = (zone_name, turn)

            if current_state in visited: #  ???
                continue

            visited.add(current_state)

            if zone_name == end:
                return self._reconstruct_path(
                    previous,
                    current_state,
                )

            if turn >= start_turn + self.max_horizen:
                continue

            current_zone = self.graph.zones[zone_name]

            wait_turn = turn + 1  #  ???
            wait_state = (zone_name, wait_turn)

            if self.reservations.zone_is_available(
                    current_zone,
                    wait_turn
            ):
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

                #  ??? 到着時のターン数がmax_horizenよりデカかったら？
                if (
                    arrival_turn
                    > start_turn + self.max_horizen
                ):
                    continue

                connection = self.graph.find_connection(
                    zone_name,
                    neighbor_name
                )

                if not self._connection_is_available_during_move(
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

    def _connection_is_available_during_move(
        self,
        connection: Connection,
        departure_turn: int,
        arrival_turn: int
    ) -> bool:
        for turn in range(
            departure_turn + 1,
            arrival_turn + 1
        ):
            if not self.reservations.connection_is_available(
                connection,
                turn
            ):
                return False

        return True

    def _reconstruct_path(
        self,
        previous: dict[
            tuple[str, int],
            tuple[str, int]
        ],
        goal_state: tuple[str, int]
    ) -> list[tuple[int, str]]:

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







def find_cheapest_path(graph: Graph, start: str, end: str) -> list[str]:
    infinity = (float("inf"), float("inf"))
    costs = {name: infinity for name in graph.zones}
    costs[start] = (0, 0)
    previous: dict[str, str] = {}
    unvisited = set(graph.zones.keys())

    while unvisited:
        current = min(unvisited, key=lambda name: costs[name])

        if costs[current] == infinity:
            break

        if current == end:
            break

        unvisited.remove(current)

        for neighdor_name in graph.get_neighbors(current):
            neighdor_zone = graph.zones[neighdor_name]

            if neighdor_zone.zone_type == "blocked":
                continue

            move_cost = MOVE_COST[neighdor_zone.zone_type]

            current_cost, current_priority = costs[current]

            if neighdor_zone.zone_type == "priority":
                priority = current_priority = -1
            else:
                priority = current_priority

            new_cost = (
                current_cost + move_cost,
                priority
            )

            if new_cost < costs[neighdor_name]:
                costs[neighdor_name] = new_cost
                previous[neighdor_name] = current

    path = [end]
    while path[-1] != start:
        path.append(previous[path[-1]])
    path.reverse()

    return path


class Drone:
    def __init__(self, drone_id: str, path: list[str]) -> None:
        self.id = drone_id
        self.path = path
        self.path_index = 0  #今pathの何番目にいるか
        self.delivered = False
        # 移動中の時にだけ使う情報
        self.in_transit_to: Optional[str] = None
        self.turns_remaining = 0
        self.transit_connection: Optional[Connection] = None


def simulate(graph: Graph, drones: list[Drone]) -> None:
    renderer = TerminalRenderer(graph)
    for drone in drones:
        graph.zones[drone.path[0]].occupants.add(drone.id)

    turn = 1
    while not all(drone.delivered for drone in drones):
        turn_moves = []

        transient_travelers: list[tuple[Connection, str]] = []

        for drone in drones:
            if drone.delivered:
                continue

            # すでに移動中(restrictedゾーンに向かっている)場合
            if drone.in_transit_to is not None:
                drone.turns_remaining -= 1

                # 到着
                if drone.turns_remaining == 0:
                    destination_name = drone.in_transit_to
                    destination_zone = graph.zones[destination_name]
                    destination_zone.occupants.add(drone.id)
                    drone.transit_connection.travelers.discard(drone.id)
                    drone.path_index += 1
                    drone.in_transit_to = None
                    drone.transit_connection = None
                    turn_moves.append(
                        f"{drone.id}-{destination_zone.display_name()}"
                    )
                    if destination_name == graph.end_zone_name:
                        drone.delivered = True

                # まだ移動中
                else:
                    connection = drone.transit_connection
                    connection_name = connection.display_name(graph)
                    turn_moves.append(f"{drone.id}-{connection_name}")
                continue

            # 止まっている場合：次に進めるか判定する
            current_zone_name = drone.path[drone.path_index]
            next_zone_name = drone.path[drone.path_index + 1]
            next_zone = graph.zones[next_zone_name]
            cost = MOVE_COST[next_zone.zone_type]
            connection = graph.find_connection(current_zone_name, next_zone_name)

            if not connection.has_capacity():
                continue  # 橋が満員なので待つ

            if not next_zone.has_capacity():
                continue

            # restrictedゾーンへ2ターンかけて移動を開始する
            if cost == 2:
                connection.travelers.add(drone.id)
                graph.zones[current_zone_name].occupants.discard(drone.id)
                drone.in_transit_to = next_zone_name
                drone.turns_remaining = cost - 1
                drone.transit_connection = connection
                connection_name = connection.display_name(graph)
                turn_moves.append(f"{drone.id}-{connection_name}")

            # 1ターンで渡り切れる移動
            else:
                connection.travelers.add(drone.id)
                transient_travelers.append((connection, drone.id))
                graph.zones[current_zone_name].occupants.discard(drone.id)
                next_zone.occupants.add(drone.id)
                drone.path_index += 1
                turn_moves.append(f"{drone.id}-{next_zone.display_name()}")
                if next_zone_name == graph.end_zone_name:
                    drone.delivered = True

        # このターンだけ橋を使った（1ターン移動の)ドローンを、橋から降ろす
        for connection, traveler_id in transient_travelers:
            connection.travelers.discard(traveler_id)

        # if turn_moves:
        #     print(f"{turn}ターン目: " + " ".join(turn_moves))
        renderer.render(turn, turn_moves)
        turn += 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python -m {__package__} <map_file>")
        sys.exit(1)

    map_file = sys.argv[1]
    nb_drones, graph = build_graph_from_map(map_file)
 
    # path = find_cheapest_path(graph, graph.start_zone_name, graph.end_zone_name)
    # print("全ドローンが通る道:", " → ".join(path))
    # print()

    # drones = [Drone(f"D{i}", path) for i in range(1, nb_drones + 1)]    
    # simulate(graph, drones)


    #  ReservationTableのテスト
    # reservations = ReservationTable()

    # reservations.reserve_zone(
    #     zone_name="A",
    #     turn=1,
    #     drone_id="D1",
    # )

    # print(reservations.zone_reservations)


    #  PathFinderのテスト
    reservations = ReservationTable()

    pathfinder = PathFinder(
        graph,
        reservations,
    )

    path = pathfinder.find_path(
        start=graph.start_zone_name,
        end=graph.end_zone_name,
        drone_id="D1",
    )

    print(path)

