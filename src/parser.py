from .models import Connection, Graph, Zone

from typing import Optional


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

