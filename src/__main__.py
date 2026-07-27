from typing import Optional

MOVE_COST = {
    "normal": 1,
    "priority": 1,
    "restricted": 2,
}


class Zone:
    def __init__(
            self,
            name:str,
            zone_type: str = "normal",
            max_drones: Optional[int] = 1,
        ) -> None:
        self.name = name
        self.zone_type = zone_type
        self.max_drones = max_drones
        self.occupants: set[str] = set()  # 今ここにいるドローンのID

    def has_capacity(self) -> bool:
        if self.max_drones is None:
            return True
        return len(self.occupants) < self.max_drones


class Connection:
    def __init__(self, zone1: str, zone2: str) -> None:
        self.zone1 = zone1
        self.zone2 = zone2

    def other_side(self, zone_name: str) -> str:
        if zone_name == self.zone1:
            return self.zone2
        
        return self.zone1

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
        return "normal"
    
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
            name = rest.split()[0]
            metadata = extract_metadata(rest)
            zone_type = metadata.get("zone", "normal")

            if is_start or is_end:
                max_drones = None
            else:
                max_drones = int(metadata.get("max_dorones", "1"))

            zone = Zone(name, zone_type, max_drones)
            graph.add_zone(zone, is_start=is_start, is_end=is_end)
        
        elif line.startswith("connection:"):
            rest = line.split(":", 1)[1].strip()
            rest = rest.split("[")[0].strip()
            zone1, zone2 = rest.split("-")
            graph.add_connection(Connection(zone1, zone2))

    assert nb_drones is not None, "nb_dronesが見つかりませんでした"
    return nb_drones, graph


def find_cheapest_path(graph: Graph, start: str, end: str) -> list[str]:
    infinity = float("inf")
    costs = {name: infinity for name in graph.zones}
    costs[start] = 0
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
            new_cost = costs[current] + move_cost

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


def simulate(graph: Graph, drones: list[Drone]) -> None:
    for drone in drones:
        graph.zones[drone.path[0]].occupants.add(drone.id)

    turn = 1
    while not all(drone.delivered for drone in drones):
        turn_moves = []

        for drone in drones:
            if drone.delivered:
                continue

            current_zone_name = drone.path[drone.path_index]
            next_zone_name = drone.path[drone.path_index + 1]
            next_zone = graph.zones[next_zone_name]

            if not next_zone.has_capacity():
                continue

            #移動できる！　元の場所から抜けて、新しい場所に入る
            graph.zones[current_zone_name].occupants.discard(drone.id)
            next_zone.occupants.add(drone.id)
            drone.path_index += 1
            turn_moves.append(f"{drone.id}-{next_zone_name}")

            if next_zone_name == graph.end_zone_name:
                drone.delivered = True

        if turn_moves:
            print(f"{turn}ターン目: " + " ".join(turn_moves))
        turn += 1


# def simulate_single_drone(graph: Graph, path: list[str]) -> None:
#     path_index = 0
#     pending_zone: str | None = None
#     turn = 1

#     while path_index < len(path) -1 or pending_zone is not None:
#         if pending_zone is not None:
#             path_index += 1
#             print(f"{turn}ターン目: D1-{pending_zone}")
#             pending_zone = None
#         else:
#             current_zone = path[path_index]
#             next_zone = path[path_index + 1]
#             next_zone_type = graph.zones[next_zone].zone_type
#             cost = MOVE_COST[next_zone_type]

#             if cost == 1:
#                 path_index += 1
#                 print(f"{turn}ターン目: D1-{next_zone}")
#             else:
#                 connection = graph.find_connection(current_zone, next_zone)
#                 connection_name = f"{connection.zone1}-{connection.zone2}"
#                 pending_zone = next_zone
#                 print(f"{turn}ターン目: D1-{connection_name}(移動中)")
#         turn += 1


if __name__ == "__main__":
    nb_drones, graph = build_graph_from_map("sample.txt")
 
    path = find_cheapest_path(graph, graph.start_zone_name, graph.end_zone_name)
    print("全ドローンが通る道:", " → ".join(path))
    print()

    drones = [Drone(f"D{i}", path) for i in range(1, nb_drones + 1)]    
    simulate(graph, drones)
