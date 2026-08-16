from __future__ import annotations
import sys

import heapq
from typing import Optional

from .models import Zone, Connection, Graph, Drone
from .visualize import TerminalRenderer


MOVE_COST = {
    "normal": 1,
    "priority": 1,
    "restricted": 2,
}

# MAX_SEARCH_TURNS = (
#     len(graph.zones)
#     * nb_drones
#     * max(MOVE_COST.values())
# )


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
        """Connectionを予約表用の文字列に変換する。"""
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
        """決定した経路を予約する

        Args:
            graph (Graph): _description_
            path (_type_): _description_

        Returns:
            _type_: _description_
        """
        for turn, zone_name in path:
            self.reserve_zone(
                zone_name,
                turn,
                drone_id
            )

        for i in range(len(path) -1):
            departure_turn, current_zone = path[i]
            arrival_turn, next_zone = path[i + 1]

            if current_zone == next_zone:  #  待機だったら
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
        self.max_horizon = max_horizon

    def find_path(
        self,
        start: str,
        end: str,
        drone_id: str,
        start_turn: int = 0
    ) -> Optional[list[tuple[int, str]]]:

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

            if current_state in expanded: # 同じ状態を二度展開しない
                continue

            expanded.add(current_state)

            if zone_name == end:
                return self._reconstruct_path(
                    previous,
                    current_state,
                )

            if turn >= start_turn + self.max_horizon:
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

                #  ??? 到着時のターン数がmax_horizonよりデカかったら？
                # 探索上限を超える到着候補は追加しない
                if (
                    arrival_turn
                    > start_turn + self.max_horizon
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


def simulate(graph: Graph, drones: list[Drone]) -> None:
    renderer = TerminalRenderer(graph)
    for drone in drones:
        _, start_zone_name = drone.path[0]
        graph.zones[start_zone_name].occupants.add(drone.id)

    turn = 0
    while not all(drone.delivered for drone in drones):
        turn_moves = []

        for drone in drones:
            if drone.delivered:
                continue

            if drone.path_index >= len(drone.path) - 1:
                drone.delivered = True
                continue

            depature_turn, current_zone_name = (
                drone.path[drone.path_index]
            )

            arrival_turn, next_zone_name = (
                drone.path[drone.path_index + 1]
            )

            # PathFinderが決めた出発時刻になるまでは動かない。
            if turn <= depature_turn:
                continue

            #  待機
            if current_zone_name == next_zone_name:
                if turn == arrival_turn:  #  ???
                    drone.path_index += 1
                continue

            connection = graph.find_connection(
                current_zone_name,
                next_zone_name
            )

            #  到着に2ターン掛かる(restrictゾーン)
            if turn < arrival_turn:
                #  初めてConnectionへ入るとき
                if drone.transit_connection is None:
                    # Aから出す
                    graph.zones[
                        current_zone_name
                    ].occupants.discard(drone.id)
                    # Connection上に置く
                    connection.travelers.add(drone.id)
                    # droneがどのConnectionを移動中か記録
                    drone.transit_connection = connection

                turn_moves.append(
                    f"{drone.id}-{connection.display_name(graph)}"
                )
                continue

            if turn == arrival_turn:
                graph.zones[
                    current_zone_name
                ].occupants.discard(drone.id)

                if drone.transit_connection is not None:
                    drone.transit_connection.travelers.discard(
                        drone.id
                    )
                    drone.transit_connection = None

                destination_zone = graph.zones[next_zone_name]
                destination_zone.occupants.add(drone.id)

                drone.path_index += 1

                turn_moves.append(
                    f"{drone.id}-{destination_zone.display_name()}"
                )

                if next_zone_name == graph.end_zone_name:
                    drone.delivered = True
        renderer.render(turn, turn_moves)
        
        turn += 1
 

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python -m {__package__} <map_file>")
        sys.exit(1)

    map_file = sys.argv[1]
    nb_drones, graph = build_graph_from_map(map_file)

    reservations = ReservationTable()

    pathfinder = PathFinder(
        graph,
        reservations
    )

    paths: dict[
        str,
        list[tuple[int, str]]
        ] = {}

    for i in range(1, nb_drones + 1):
        drone_id = f"D{i}"

        path = pathfinder.find_path(
            graph.start_zone_name,
            graph.end_zone_name,
            drone_id
        )

        if path is None:
            print(
                f"{drone_id}:"
                "経路が見つかりませんでした"
            )
            continue

        reservations.reserve_path(
            graph,
            path,
            drone_id
        )

        paths[drone_id] = path

    drones = []

    for drone_id, path in paths.items():
        drones.append(
            Drone(
                drone_id,
                path
            )
        )

    print("\033[?7l", end="")

    try:
        simulate(graph, drones)
    finally:
        print("\033[?7h", end="")

            

    # 全台同経路使用
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
    # reservations = ReservationTable()

    # pathfinder = PathFinder(
    #     graph,
    #     reservations,
    # )

    # path = pathfinder.find_path(
    #     start=graph.start_zone_name,
    #     end=graph.end_zone_name,
    #     drone_id="D1",
    # )

    # print(path)

