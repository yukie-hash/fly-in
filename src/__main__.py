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

    def get_neighdors(self, zone_name: str) -> list[str]:
        neighdors = []

        for connection in self.connections:
            if connection.zone1 == zone_name or connection.zone2 == zone_name:
                neighdors.append(connection.other_side(zone_name))
        return neighdors
    
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
    nb_drones = None

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

    assert nb_drones is not None, "nb_dronesが見つかりませんでした"
    return nb_drones, graph


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

        for neighdor_name in graph.get_neighdors(current):
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
    nb_drones, graph = build_graph_from_map("03_priority_puzzle.txt")
 
    path = find_cheapest_path(graph, graph.start_zone_name, graph.end_zone_name)
    print("全ドローンが通る道:", " → ".join(path))
    print()

    drones = [Drone(f"D{i}", path) for i in range(1, nb_drones + 1)]    
    simulate(graph, drones)
