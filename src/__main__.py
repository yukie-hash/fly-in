from __future__ import annotations
import sys

from .models import Drone
from .parser import build_graph_from_map
from .planning import ReservationTable, PathFinder
from .simulation import simulate

 
def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: python -m {__package__} <map_file>")
        sys.exit(1)

    map_file = sys.argv[1]

    try:
        nb_drones, graph = build_graph_from_map(map_file)
    except FileNotFoundError:
        print(f"Error: file not found: {map_file}")
        sys.exit(1)
    except ValueError as error:
        print(f"Error: invalid map: {error}")
        sys.exit(1)

    reservations = ReservationTable()

    pathfinder = PathFinder(
        graph,
        reservations
    )

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

    drones = []

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


if __name__ == "__main__":
    main()
