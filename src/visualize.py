"""ターミナル上でグラフとドローン配置を描画する。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .__main__ import Connection, Graph, Zone


RESET = "\033[0m"
ZONE_COLORS = {
    "black": "\033[30m", "blue": "\033[94m", "brown": "\033[38;5;130m",
    "crimson": "\033[38;5;197m", "cyan": "\033[96m", "darkred": "\033[38;5;88m",
    "gold": "\033[38;5;220m", "gray": "\033[90m", "green": "\033[92m",
    "lime": "\033[92m", "maroon": "\033[38;5;52m", "orange": "\033[38;5;208m",
    "purple": "\033[95m", "red": "\033[91m", "violet": "\033[38;5;141m",
    "white": "\033[97m", "yellow": "\033[93m",
}


class TerminalRenderer:
    """グラフの状態をターミナル用の文字グリッドへ変換する責務を持つ。"""

    box_width = 13
    cell_width = 20
    cell_height = 6
    top_margin = 3

    def __init__(self, graph: Graph) -> None:
        self.graph = graph
        self.zones = list(graph.zones.values())
        self.min_x = min(zone.x for zone in self.zones)
        self.max_x = max(zone.x for zone in self.zones)
        self.min_y = min(zone.y for zone in self.zones)
        self.max_y = max(zone.y for zone in self.zones)
        self.width = (self.max_x - self.min_x + 1) * self.cell_width
        self.height = (
            (self.max_y - self.min_y + 1) * self.cell_height
            + self.top_margin * 2
        )
        self.grid: list[list[str]] = []
        self.overlays: list[tuple[int, int, str, str]] = []

    def render(self, turn: int, moves: list[str]) -> None:
        """指定ターンのフレームを組み立てて出力する。"""
        self.grid = [[" " for _ in range(self.width)] for _ in range(self.height)]
        self.overlays = []
        self._draw_connections()
        self._draw_zones()
        self._print_frame(turn, moves)

    def _center(self, zone_name: str) -> tuple[int, int]:
        zone = self.graph.zones[zone_name]
        return (
            self.top_margin + (self.max_y - zone.y) * self.cell_height + 2,
            (zone.x - self.min_x) * self.cell_width + self.cell_width // 2,
        )

    def _put(self, row: int, col: int, text: str) -> None:
        if not 0 <= row < self.height:
            return
        for offset, character in enumerate(text):
            target_col = col + offset
            if 0 <= target_col < self.width:
                self.grid[row][target_col] = character

    def _draw_segment(
            self, row_a: int, col_a: int, row_b: int, col_b: int, edge: str
        ) -> None:
        """水平または垂直の線分を、両端を除いて描く。"""
        steps = max(abs(row_b - row_a), abs(col_b - col_a))
        for step in range(1, steps):
            row = row_a + (0 if row_a == row_b else (1 if row_b > row_a else -1) * step)
            col = col_a + (0 if col_a == col_b else (1 if col_b > col_a else -1) * step)
            if 0 <= row < self.height and 0 <= col < self.width:
                current = self.grid[row][col]
                if current == " ":
                    self.grid[row][col] = edge
                # 異なる方向の線が交差する場合のみ '┼' にする（同じ種類の線の重複なら化けさせない）
                elif current in ("─", "│", "═", "║") and current != edge:
                    self.grid[row][col] = "┼"

    def _draw_connection(self, connection: Connection) -> None:
        start_row, start_col = self._center(connection.zone1)
        end_row, end_col = self._center(connection.zone2)
        horizontal = start_row == end_row
        vertical = start_col == end_col
        horizontal_edge, vertical_edge = (
            ("═", "║") if connection.has_explicit_capacity else ("─", "│")
        )

        if horizontal:
            self._draw_segment(start_row, start_col, end_row, end_col, horizontal_edge)
        elif vertical:
            self._draw_segment(start_row, start_col, end_row, end_col, vertical_edge)
        else:
            # 斜め接続は横線→縦線のL字通路にする。
            bend_row, bend_col = start_row, end_col
            self._draw_segment(start_row, start_col, bend_row, bend_col, horizontal_edge)
            self._draw_segment(bend_row, bend_col, end_row, end_col, vertical_edge)
            
            # 曲がり角文字の書き込み（既存の線がある場合は交差点として潰さないように判定）
            corner_char = self._corner(
                end_col > start_col,
                end_row > start_row,
                connection.has_explicit_capacity,
            )
            if 0 <= bend_row < self.height and 0 <= bend_col < self.width:
                if self.grid[bend_row][bend_col] == " ":
                    self.grid[bend_row][bend_col] = corner_char

        if connection.has_explicit_capacity:
            label_row = round((start_row + end_row) / 2) - 3
            label_col = round((start_col + end_col) / 2) - 3
            self._put(label_row, label_col, f"(cap:{connection.max_link_capacity})")

    @staticmethod
    def _corner(moves_right: bool, moves_down: bool, double: bool) -> str:
        if double:
            return "╗" if moves_right and moves_down else "╝" if moves_right else "╔" if moves_down else "╚"
        return "┐" if moves_right and moves_down else "┘" if moves_right else "┌" if moves_down else "└"

    def _draw_connections(self) -> None:
        for connection in self.graph.connections:
            self._draw_connection(connection)

    def _box_characters(self, zone: Zone) -> tuple[str, str, str, str, str, str, str]:
        """ゾーン種別に対応する上辺・側辺・下辺の罫線を返す。"""
        if zone.name in (self.graph.start_zone_name, self.graph.end_zone_name):
            return "╔", "═", "╗", "║", "╚", "═", "╝"
        if zone.zone_type == "blocked":
            return "┌", "┄", "┐", "┆", "└", "┄", "┘"
        if zone.zone_type == "priority":
            return "╭", "─", "╮", "│", "╰", "─", "╯"
        if zone.zone_type == "restricted":
            return "┏", "━", "┓", "┃", "┗", "━", "┛"
        return "┌", "─", "┐", "│", "└", "─", "┘"

    def _draw_zone(self, zone: Zone) -> None:
        row, col = self._center(zone.name)
        left = col - self.box_width // 2
        top = row - 1
        top_left, horizontal, top_right, vertical, bottom_left, bottom_horizontal, bottom_right = self._box_characters(zone)
        capacity = "∞" if zone.max_drones is None else str(zone.max_drones)
        title = zone.name[:self.box_width].center(self.box_width)
        zone_type = f"({zone.zone_type})"[:self.box_width].center(self.box_width)
        middle = self._occupancy_text(len(zone.occupants), capacity).center(
            self.box_width - 2
        )
        lines = (
            (top - 2, title),
            (top - 1, zone_type),
            (top, top_left + horizontal * (self.box_width - 2) + top_right),
            (top + 1, vertical + middle + vertical),
            (top + 2, bottom_left + bottom_horizontal * (self.box_width - 2) + bottom_right),
        )
        color = ZONE_COLORS.get(zone.color, "")
        for line_row, text in lines:
            self._put(line_row, left, text)
            self.overlays.append((line_row, left, text, color))

    @staticmethod
    def _occupancy_text(drone_count: int, capacity: str) -> str:
        """ドローン数に応じた▲と、正確な現在数・上限を返す。"""
        if drone_count == 0:
            return f"0/{capacity}"
        visible_markers = "▲" * min(drone_count, 5)
        overflow = "…" if drone_count > 5 else ""
        return f"{visible_markers}{overflow} {drone_count}/{capacity}"

    def _draw_zones(self) -> None:
        for zone in self.zones:
            self._draw_zone(zone)

    def _print_frame(self, turn: int, moves: list[str]) -> None:
        print(f"\n=== {turn}ターン目 ===")
        if moves:
            print("移動:", " ".join(moves))

        for row_index, row_chars in enumerate(self.grid):
            line = "".join(row_chars).rstrip()
            row_overlays = [item for item in self.overlays if item[0] == row_index]
            for _, col, text, color in sorted(row_overlays, reverse=True):
                if color:
                    line = line[:col] + color + text + RESET + line[col + len(text):]
            print(line)


