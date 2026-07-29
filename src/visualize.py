"""Day6: マップのネットワークと、ドローンの今の位置を色つきでターミナルに表示する。

考え方:
1. 各場所には x, y という座標がある → その座標通りに文字を配置する
2. 場所の種類ごとに色を変える
3. 今そこにドローンがいれば、名前の横に色つきでIDを表示する
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .__main__ import Graph

# ANSIエスケープコード（ターミナルで文字に色をつけるための特殊な文字列）
RESET = "\033[0m"
ZONE_COLORS = {
    "normal": "\033[94m",  # 青
    "priority": "\033[92m",  # 緑
    "restricted": "\033[93m",  # 黄色
    "blocked": "\033[91m",  # 赤
}
START_END_COLOR = "\033[97m"  # 白
DRONE_COLOR = "\033[95m"  # マゼンタ（ドローンがいることを目立たせる色）

CELL_WIDTH = 13  # 座標1つぶんの、横方向の文字数
CELL_HEIGHT = 3  # 座標1つぶんの、縦方向の行数


def zone_color(graph: Graph, zone_name: str) -> str:
    """そのゾーンに使う色（ANSIコード）を返す。"""
    zone = graph.zones[zone_name]
    if zone_name in (graph.start_zone_name, graph.end_zone_name):
        return START_END_COLOR
    return ZONE_COLORS.get(zone.zone_type, ZONE_COLORS["normal"])


def render_map(graph: Graph, turn: Optional[int] = None) -> None:
    """今のドローンの位置を反映した地図を、ターミナルに描く。

    Args:
        graph: 対象のGraph（zones に occupants が入っている前提）。
        turn: 表示するターン番号（省略可）。
    """
    zones = list(graph.zones.values())
    min_x = min(zone.x for zone in zones)
    max_x = max(zone.x for zone in zones)
    min_y = min(zone.y for zone in zones)
    max_y = max(zone.y for zone in zones)

    width = (max_x - min_x + 1) * CELL_WIDTH
    height = (max_y - min_y + 1) * CELL_HEIGHT

    # 空白で埋めた、文字の2次元グリッドを作る
    grid = [[" " for _ in range(width)] for _ in range(height)]

    def place_text(row: int, col: int, text: str) -> None:
        """指定した位置から、gridに文字を1文字ずつ置いていく。"""
        for offset, character in enumerate(text):
            if 0 <= col + offset < width:
                grid[row][col + offset] = character

    labels: list[tuple[int, int, str, str]] = []  # (row, col, text, color)

    for zone in zones:
        col = (zone.x - min_x) * CELL_WIDTH
        row = (max_y - zone.y) * CELL_HEIGHT  # yが大きいほど上に表示する

        color = zone_color(graph, zone.name)
        place_text(row, col, zone.name)
        labels.append((row, col, zone.name, color))

        if zone.occupants:
            drone_text = "[" + ",".join(sorted(zone.occupants)) + "]"
            place_text(row + 1, col, drone_text)
            labels.append((row + 1, col, drone_text, DRONE_COLOR))

    if turn is not None:
        print(f"=== {turn}ターン目終了時点 ===")

    # 1行ずつ、色をつけながら出力する
    for row_index, row_chars in enumerate(grid):
        colored_line = "".join(row_chars)
        # 同じ行にある複数のラベルは、右側（列が大きい方）から順に
        # 色を差し込む。左から差し込むと、あとから足した色コードの分
        # 文字数が増えて、後続ラベルの位置がズレてしまうため。
        row_labels = [label for label in labels if label[0] == row_index]
        row_labels.sort(key=lambda label: label[1], reverse=True)
        for _, label_col, text, color in row_labels:
            colored_line = (
                colored_line[:label_col]
                + color
                + text
                + RESET
                + colored_line[label_col + len(text):]
            )
        print(colored_line)

    print()


if __name__ == "__main__":
    from .__main__ import build_graph_from_map

    _, graph = build_graph_from_map("sample_map.txt")

    # 動作確認: D1, D2, D3 を手動でいくつかのゾーンに置いてみる
    graph.zones["hub"].occupants.add("D3")
    graph.zones["corridorA"].occupants.add("D1")
    graph.zones["roof1"].occupants.add("D2")

    render_map(graph, turn=1)
