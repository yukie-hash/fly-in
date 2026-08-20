from .models import Graph, Drone
from .visualize import TerminalRenderer


class Simulator:
    """Execute planned drone routes one discrete turn at a time."""

    def simulate(self, graph: Graph, drones: list[Drone]) -> None:
        """Simulate all routes and print visual and movement output.

        Args:
            graph: Graph containing mutable occupancy state.
            drones: Drones with precomputed, scheduled paths.
        """
        renderer = TerminalRenderer()
        simulation_output: list[str] = []

        for drone in drones:
            _, start_zone_name = drone.path[0]
            graph.zones[start_zone_name].occupants.add(drone.id)

        turn = 1
        while not all(drone.delivered for drone in drones):
            turn_moves = []

            for drone in drones:
                if drone.delivered:
                    continue

                if drone.path_index >= len(drone.path) - 1:
                    drone.delivered = True
                    continue

                depature_turn, current_zone_name = (
                    drone.path[drone.path_index]
                )

                arrival_turn, next_zone_name = (
                    drone.path[drone.path_index + 1]
                )

                # PathFinderが決めた出発時刻になるまでは動かない。
                if turn <= depature_turn:
                    continue

                #  待機
                if current_zone_name == next_zone_name:
                    if turn == arrival_turn:
                        drone.path_index += 1
                    continue

                connection = graph.find_connection(
                    current_zone_name,
                    next_zone_name
                )

                #  到着に2ターン掛かる(restrictゾーン)
                if turn < arrival_turn:
                    #  初めてConnectionへ入るとき
                    if drone.transit_connection is None:
                        # Aから出す
                        graph.zones[
                            current_zone_name
                        ].occupants.discard(drone.id)
                        # Connection上に置く
                        connection.travelers.add(drone.id)
                        # droneがどのConnectionを移動中か記録
                        drone.transit_connection = connection

                    turn_moves.append(
                        f"{drone.id}-{connection.zone1}-{connection.zone2}"
                    )
                    continue

                if turn == arrival_turn:
                    graph.zones[
                        current_zone_name
                    ].occupants.discard(drone.id)

                    if drone.transit_connection is not None:
                        drone.transit_connection.travelers.discard(
                            drone.id
                        )
                        drone.transit_connection = None

                    destination_zone = graph.zones[next_zone_name]
                    destination_zone.occupants.add(drone.id)

                    drone.path_index += 1

                    turn_moves.append(
                        f"{drone.id}-{next_zone_name}"
                    )

                    if next_zone_name == graph.end_zone_name:
                        drone.delivered = True
            renderer.render_map(graph, turn)

            if turn_moves:
                simulation_output.append(
                    " ".join(turn_moves)
                )

            turn += 1

        print("\nSimulation Output:")
        for line in simulation_output:
            print(line)
