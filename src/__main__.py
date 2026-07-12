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

class Graph:
    def __init__(self) -> None:
        self.zones: dict[str, Zone] = {}
        self.connections: list[Connection] = []

    def add_zone(self, zone: Zone) -> None:
        self.zones[zone.name] = zone

    def add_connection(self, connection: Connection) -> None:
        self.connections.append(connection)


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
            nb_drones = int(line.split(":")[1].split())
        
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


if __name__ == "__main__":
    main()