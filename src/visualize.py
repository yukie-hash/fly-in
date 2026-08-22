from .models import Graph
from .terminal import TerminalColorizer


RESET = "\033[0m"


class TerminalRenderer:
    """Render graph occupancy as a colorized terminal snapshot."""

    def __init__(self) -> None:
        self.colorizer = TerminalColorizer()

    def render_map(self, graph: Graph, turn: int) -> None:
        """Print zone occupancy and connection occupqncy
        for one simulation turn.

        Args:
            graph: Graph whose current state is displayed.
            turn: Current simulation turn number.
        """
        print(f"\n=== {turn}ターン目 ===")

        print("Zones:")

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
                f"{self.colorizer.colorize(zone.name, zone.color)}:{RESET} "
                f"{len(zone.occupants)}/{capacity}"
                f"{drone_info}"
            )

        for connection in graph.connections:
            if connection.travelers:
                print("\nConnections:")

                if connection.max_link_capacity is None:
                    capacity = "∞"
                else:
                    capacity = str(connection.max_link_capacity)

                occupants = " ".join(
                    f"{drone_id}"
                    for drone_id in connection.travelers
                )

                print(
                    f"{connection.zone1}-{connection.zone2} "
                    f"{len(connection.travelers)}/{capacity} "
                    f"[{occupants}]"
                )
