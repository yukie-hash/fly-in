from .models import Connection, Graph, Zone

from typing import Optional

import re


ZONE_PATTERN = re.compile(
    r"^(?P<name>[^\s-]+)\s+"
    r"(?P<x>[+-]?\d+)\s+"
    r"(?P<y>[+-]?\d+)"
    r"(?:\s+\[(?P<metadata>[^\]]*)\])?$"
)

CONNECTION_PATTERN = re.compile(
    r"^(?P<zone1>[^\s-]+)-"
    r"(?P<zone2>[^\s-]+)"
    r"(?:\s+\[(?P<metadata>[^\]]*)\])?$"
)


class MapParsor():
    def extract_metadata(
            self,
            metadata_str: Optional[str],
            line_number: int
    ) -> dict[str, str]:
        if not metadata_str:
            return {}

        metadata = {}

        for token in metadata_str.split():
            #  構文チェック
            if "=" not in token:
                raise ValueError(
                    f"line {line_number}: invalid metadata '{token}'"
                )
            if token.count("=") != 1:
                raise ValueError(
                    f"line {line_number}: invalid metadata '{token}'"
                )

            key, value = token.split("=")

            if key in metadata:
                raise ValueError(
                    f"line {line_number}: duplicate metadata key '{key}'"
                )

            if not key or not value:
                raise ValueError(
                    f"line {line_number}: invalid metadata '{token}'"
                )

            metadata[key] = value
        return metadata

    def build_graph_from_map(self, filepath: str) -> tuple[int, Graph]:
        graph = Graph()
        nb_drones: Optional[int] = None

        with open(filepath, encoding="utf-8") as file:
            lines = file.readlines()

        first_data_line_seen = False

        for line_number, raw_line in enumerate(lines, start=1):
            line = raw_line.split("#")[0].strip()
            if not line:
                continue

            if not first_data_line_seen:
                if not line.startswith("nb_drones:"):
                    raise ValueError(
                        f"line {line_number}: "
                        "first data line must define nb_drones"
                    )

                if line.startswith("nb_drones:"):
                    try:
                        nb_drones = int(line.split(":")[1].strip())
                    #  intではない
                    except ValueError:
                        raise ValueError(
                            f"line{line_number}: nb_drones must be an integer"
                        )
                    #  整数ではない
                    if nb_drones <= 0:
                        raise ValueError(
                            f"line{line_number}: nb_drones must be positive"
                        )
                first_data_line_seen = True

            elif line.startswith(("start_hub:", "end_hub:", "hub:")):
                is_start = line.startswith("start_hub:")
                is_end = line.startswith("end_hub:")

                rest = line.split(":", 1)[1].strip()
                match = ZONE_PATTERN.fullmatch(rest)
                if match is None:
                    raise ValueError(
                        f"line {line_number}: invalid zone syntax"
                    )

                if is_start and graph.start_zone_name is not None:
                    raise ValueError(
                        f"line {line_number}: start_hub must be defined once"
                    )
                if is_end and graph.end_zone_name is not None:
                    raise ValueError(
                        f"line {line_number}: end_hub must be defined once"
                    )

                name = match.group("name")
                #  zone_nameの重複がないか
                if name in graph.zones:
                    raise ValueError(
                        f"line {line_number}: duplicate zone '{name}'"
                    )

                x = int(match.group("x"))
                y = int(match.group("y"))

                metadata = self.extract_metadata(
                    match.group("metadata"),
                    line_number,
                )

                #  zone_typeのパース
                valid_zone_types = {
                    "normal",
                    "blocked",
                    "restricted",
                    "priority"
                }
                zone_type = metadata.get("zone", "normal")
                if zone_type not in valid_zone_types:
                    raise ValueError(
                        f"line{line_number}: invalid zone type '{zone_type}'"
                    )

                color = metadata.get("color")

                #  max_dronesのパース
                if is_start or is_end:
                    max_drones = None
                else:
                    try:
                        max_drones = int(metadata.get("max_drones", "1"))
                    except ValueError:
                        raise ValueError(
                            f"line{line_number}: max_drones must be an integer"
                            )
                    if max_drones <= 0:
                        raise ValueError(
                            f"line {line_number}: max_drones must be positive"
                        )

                zone = Zone(name, x, y, zone_type, max_drones, color)
                graph.add_zone(zone, is_start=is_start, is_end=is_end)

            elif line.startswith("connection:"):
                rest = line.split(":", 1)[1].strip()
                match = CONNECTION_PATTERN.fullmatch(rest)
                if match is None:
                    raise ValueError(
                        f"line {line_number}: invalid connection syntax"
                    )

                zone1 = match.group("zone1")
                zone2 = match.group("zone2")
                metadata = self.extract_metadata(
                    match.group("metadata"),
                    line_number,
                )

                #  定義済みのzoneのみをリンクする
                if zone1 not in graph.zones or zone2 not in graph.zones:
                    raise ValueError(
                        f"line {line_number}: "
                        "connection uses undefined zone"
                        )

                #  Connectionの重複チェック
                for connection in graph.connections:
                    if {
                        connection.zone1,
                        connection.zone2,
                    } == {zone1, zone2}:
                        raise ValueError(
                            f"line {line_number}: "
                            f"duplicate connection '{zone1}-{zone2}'"
                        )

                try:
                    max_link_capacity = int(
                        metadata.get("max_link_capacity", "1")
                    )
                except ValueError:
                    raise ValueError(
                        f"line {line_number}: "
                        "max_link_capacity must be an integer"
                    )
                if max_link_capacity <= 0:
                    raise ValueError(
                        f"line {line_number}: "
                        "max_link_capacity must be positive"
                    )

                graph.add_connection(
                    Connection(
                        zone1,
                        zone2,
                        max_link_capacity,
                        has_explicit_capacity="max_link_capacity" in metadata,
                    )
                )

            else:
                raise ValueError(
                    f"line {line_number}: invalid syntax"
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
