from __future__ import annotations
import sys

from .parser import build_graph_from_map
from .planning import MultiDronePathPlanner
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

    planner = MultiDronePathPlanner(graph)

    drones = planner.plan_drone_paths(nb_drones)

    print("\033[?7l", end="")

    try:
        simulate(graph, drones)
    finally:
        print("\033[?7h", end="")


if __name__ == "__main__":
    main()
