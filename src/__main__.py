MOVE_COST = {
    "normal": 1,
    "priority": 1,
    "restricted": 2,
}


class Zone:
    def __init__(self, name:str, zone_type: str = "normal") -> None:
        self.name = name
        self.zone_type = zone_type


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

    def add_zone(self, zone: Zone) -> None:
        self.zones[zone.name] = zone

    def add_connection(self, connection: Connection) -> None:
        self.connections.append(connection)

    def get_neighdors(self, zone_name: str) -> list[str]:
        neighdors = []

        for connection in self.connections:
            if connection.zone1 == zone_name or connection.zone2 == zone_name:
                neighdors.append(connection.other_side(zone_name))
        return neighdors


def extract_zone_type(rest: str) -> str:
    if "[" not in rest:
        return "normal"
    
    metadata_str = rest.split("[")[1].split("]")[0]
    for token in metadata_str.split():
        if token.startswith("zone="):
            return token.split("=")[1]
    return "normal"


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
            rest = line.split(":", 1)[1].strip()
            name = rest.split()[0]
            zone_type = extract_zone_type(rest)
            graph.add_zone(Zone(name, zone_type))
        
        elif line.startswith("connection:"):
            rest = line.split(":", 1)[1].strip()
            rest = rest.split("[")[0].strip()
            zone1, zone2 = rest.split("-")
            graph.add_connection(Connection(zone1, zone2))

    assert nb_drones is not None, "nb_dronesが見つかりませんでした"
    return nb_drones, graph


def find_cheapest_path(graph: Graph, start: str, end: str) -> tuple[list[str], int]:
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
    print(graph.zones)
    print(graph.connections)
    print(previous)
    print(costs)
    while path[-1] != start:
        path.append(previous[path[-1]])
    path.reverse()

    return path, costs[end]


if __name__ == "__main__":
    nb_drones, graph = build_graph_from_map("01_linear_path.txt")
 
    path, total_cost = find_cheapest_path(graph, "start", "goal")
 
    print("一番安い道:", " → ".join(path))
    print("合計コスト:", total_cost, "ターン")
