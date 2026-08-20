from __future__ import annotations
import sys

from .parser import MapParsor
from .planning import MultiDronePathPlanner
from .simulation import Simulator


def main() -> None:
    """Run the command-line drone planning and simulation workflow."""
    if len(sys.argv) != 2:
        print(f"Usage: python -m {__package__} <map_file>")
        sys.exit(1)

    map_file = sys.argv[1]

    parsor = MapParsor()

    try:
        nb_drones, graph = parsor.build_graph_from_map(map_file)
    except FileNotFoundError:
        print(f"Error: file not found: {map_file}")
        sys.exit(1)
    except (
        IsADirectoryError,
        PermissionError,
        UnicodeDecodeError,
        OSError
    ) as error:
        print(f"Error: {error}")
    except ValueError as error:
        print(f"Error: invalid map: {error}")
        sys.exit(1)

    planner = MultiDronePathPlanner(graph)

    try:
        drones = planner.plan_drone_paths(nb_drones)
    except ValueError as error:
        print(f"Error: {error}")
        sys.exit(1)

    print("\033[?7l", end="")

    simulator = Simulator()

    try:
        simulator.simulate(graph, drones)
    finally:
        print("\033[?7h", end="")


if __name__ == "__main__":
    main()
