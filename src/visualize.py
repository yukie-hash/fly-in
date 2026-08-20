from .models import Graph


RESET = "\033[0m"


def render_map(graph: Graph, turn: int) -> None:
    """_summary_

    Args:
        turn (int): _description_
        turn_moves (list): _description_
    """
    print(f"\n=== {turn}ターン目 ===")

    print(f"Zones:")

    for zone in graph.zones.values():
        capacity = "∞" if zone.max_drones is None else str(zone.max_drones)

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
            f"{zone.display_name()}:{RESET} "
            f"{len(zone.occupants)}/{capacity}"
            f"{drone_info}"
        )
