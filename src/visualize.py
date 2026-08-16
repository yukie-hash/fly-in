from .models import Graph


RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"


def render_map(graph: Graph, turn: int, turn_moves: list[str]) -> None:
    """_summary_

    Args:
        turn (int): _description_
        turn_moves (list): _description_
    """
    print(f"\n=== {turn}ターン目 ===")
    print(" ".join(turn_moves))

    print()

    print(f"{YELLOW}Zones:{RESET}")

    for zone in graph.zones.values():
        capacity = (
            "1"
            if zone.max_drones is None
            else str(zone.max_drones)
        )

        if zone.name in (graph.start_zone_name, graph.end_zone_name):
            capacity = "∞"

        occupants = " ".join(
            f"{drone_id}"
            for drone_id in zone.occupants
        )

        drone_info = (
            f" [{occupants}]"
            if occupants
            else ""
        )

        print(
            f"{GREEN}{zone.name}:{RESET} "
            f"{len(zone.occupants)}/{capacity}"
            f"{drone_info}"
        )
