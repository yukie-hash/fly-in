*This project has been created as part of the 42 curriculum by yhamada.*

## Description

### Overview

Fly-in is a path-planning and simulation program designed to deliver multiple drones from a start zone to an end zone in as few turns as possible. Drones can move simultaneously, but zones and connections have capacity limits. Therefore, the program plans not only the route of each drone but also its departure and arrival turns.

### Input Map and Graph

The program reads the number of drones, zones, coordinates, metadata, and bidirectional connections between zones from a text-based map file. The parsed data is managed as `Graph`, `Zone`, and `Connection` objects.

The parser validates the number of drones, coordinates, zone names, zone types, capacities, duplicate definitions, connections to undefined zones, and other input constraints. If invalid input is detected, it returns an error indicating the cause.

### Zone Types

There are four types of zones:

- `normal`: A standard zone. Moving into it takes 1 turn.
- `blocked`: A zone that cannot be entered.
- `restricted`: Moving into this zone takes 2 turns.
- `priority`: Moving into this zone takes 1 turn, and it is preferred among equivalent route candidates.

### Capacity Constraints

By default, only one drone can occupy a normal zone at a time. If `max_drones` is specified, up to the specified number of drones can occupy the zone simultaneously. The start and end zones have unlimited capacity.

The `max_link_capacity` of a connection limits the number of drones that can use that connection during the same turn. When moving into a `restricted` zone, connection capacity is reserved for all turns during the movement.

### Pathfinding and Reservation Table

The route of each drone is planned using a shortest-path search in which the state consists of the zone name and arrival turn. In addition to zone movement costs, the search takes into account reservations made by previously planned drones.

The reservation table records which drone uses each zone or connection at each turn. When searching for a new route, only zones and connections with available capacity are considered. If the drone cannot move immediately, waiting in its current zone for one turn is also considered as a possible transition.

### Simulation

The simulator updates the state of each drone one turn at a time according to its planned route. When a drone departs, it is removed from its current zone and added to the destination zone when the movement is completed. When moving into a `restricted` zone, a drone in transit is recorded as a user of the connection.

The simulation ends when all drones have reached the end zone. Movements for each turn are output in the format `D<ID>-<zone>` or `D<ID>-<connection>`.

### Visualization

For each turn, the terminal displays the current occupancy, maximum capacity, and IDs of the drones occupying every zone. If a zone has a `color` value, an ANSI color is applied to make changes in the network state easier to follow. The start and end zones are displayed with `∞` to represent unlimited capacity.

## Instructions

### Requirements

- Python 3.10 or later
- pip
- make

### Installing Dependencies

```bash
make install
```

This installs the development dependencies defined in `pyproject.toml`.

### Running with the Default Map

```bash
make run
```

By default, `maps/easy/01_linear_path.txt` is used.

### Running with a Specified Map

```bash
make run MAP=maps/medium/02_circular_loop.txt
```

Specify the path to the input file using `MAP`.

### Running Directly with Python

```bash
python3 -m src maps/easy/01_linear_path.txt
```

### Debugging

```bash
make debug MAP=maps/easy/01_linear_path.txt
```

This starts the program using Python's standard `pdb` debugger.

### Code Quality Checks

```bash
make lint
```

This runs `flake8` and `mypy` with the required options.

### Strict Type Checking

```bash
make lint-strict
```

This runs `flake8` and `mypy --strict`.

### Cleaning Generated Files

```bash
make clean
```

This removes `__pycache__`, mypy and other cache files, and `egg-info`.

## Resources

- 初心者のためのダイクストラアルゴリズム
https://qiita.com/knhr__/items/cb3ce311508337128714
- 【Python】NetworkX 2.0の基礎的な使い方まとめ
https://qiita.com/kzm4269/items/081ff2fdb8a6b0a6112f
- 離散数学入門#5: 最短経路問題：ダイクストラ法とワーシャル–フロイド法
https://www.youtube.com/watch?v=e6X2gDTZYCQ&list=LL&index=1
-  ダイクストラアルゴリズムの仕組み   
https://www.youtube.com/watch?v=EFg3u_E6eHU

### AI Resources

- Consultation on function and variable naming
- Consultation on directory structure
- Explanation of implementation examples using Python's regular expression module
- Generation and explanation of Dijkstra's algorithm implementation examples, and discussion to support understanding
- Comparison of pathfinding and reservation strategies
- Discussion of the rationale for the search horizon
- Identification of edge cases
- Checking and fixing `flake8` and `mypy` issues
- Code review
- Creation of docstrings
- Summarization and translation of the subject

## Algorithm Choice and Implementation Strategy

### Pathfinding: Dijkstra's Algorithm

This program uses Dijkstra's algorithm for pathfinding because it can account for different movement times depending on the zone type. Moving into a `normal` or `priority` zone takes 1 turn, moving into a `restricted` zone takes 2 turns, and `blocked` zones cannot be entered. Since movement costs are not uniform, Dijkstra's algorithm is suitable for finding shortest paths in this weighted graph.

Because the reservation status of a zone may differ depending on the arrival turn, each search state is represented as `(zone name, arrival turn)`. In addition to movement, waiting for 1 turn is included as a possible transition, allowing the search to find routes that wait for capacity to become available when the network is congested. Among candidates that arrive on the same turn, routes passing through `priority` zones are preferred.

### Multi-Drone Path Planning: Sequential Planning with a Reservation Table

If multiple drones choose the same shortest path, they may become concentrated on the same route, causing delays due to zone and connection capacity limits. To address this, the program uses a reservation table and plans the drones sequentially, one at a time.

Once a drone's route has been determined, the zones and connections it will use are reserved for each corresponding turn. Subsequent drones search for their routes while taking existing reservations into account. This excludes routes that would exceed zone or connection capacities at any given turn during the planning stage. If a route is congested, a drone may wait for capacity to become available or choose another route if doing so allows it to arrive earlier. This helps prevent drones from becoming concentrated on a single route and allows multiple routes to be used in parallel.

Because moving into a `restricted` zone takes 2 turns, the required connection is reserved for the necessary turns during transit so that other drones do not exceed its connection capacity.

### Advantages and Limitations

Compared with searching the states of all drones simultaneously, this approach reduces computational and implementation complexity while allowing drones to move in parallel across multiple routes without violating capacity constraints.

However, once a route has been determined for an earlier drone, it is not replanned when subsequent drones are considered. As a result, the final result may depend on the order in which drones are planned, and the program does not guarantee the minimum possible number of turns for all drones to reach the destination.

## Visualization

For each turn, the program displays the current number of drones in each zone, its maximum capacity, and the drones currently occupying it. This makes it easier to track drone positions and congestion turn by turn, which can be difficult to understand from the Simulation Output alone. If a zone has a `color` value specified in the map, the corresponding color is applied to make zones easier to distinguish visually.

### Example

```text
=== Turn 1 ===
Zones:
start: 0/∞
junction: 2/2 [D1 D2]
path_a: 0/1
path_b: 0/1
goal: 0/∞

=== Turn 2 ===
Zones:
start: 0/∞
junction: 0/2
path_a: 1/1 [D1]
path_b: 1/1 [D2]
goal: 0/∞

=== Turn 3 ===
Zones:
start: 0/∞
junction: 0/2
path_a: 0/1
path_b: 0/1
goal: 2/∞ [D1 D2]
```