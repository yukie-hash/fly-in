"""ターミナル上でグラフとドローン配置を描画する。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .__main__ import Connection, Graph, Zone


RESET = "\033[0m"

ZONE_COLORS = {
    "black": "\033[30m",
    "blue": "\033[94m",
    "brown": "\033[38;5;130m",
    "crimson": "\033[38;5;197m",
    "cyan": "\033[96m",
    "darkred": "\033[38;5;88m",
    "gold": "\033[38;5;220m",
    "gray": "\033[90m",
    "green": "\033[92m",
    "lime": "\033[92m",
    "maroon": "\033[38;5;52m",
    "orange": "\033[38;5;208m",
    "purple": "\033[95m",
    "red": "\033[91m",
    "violet": "\033[38;5;141m",
    "white": "\033[97m",
    "yellow": "\033[93m",
}


@dataclass(frozen=True)
class RenderConfig:
    """描画レイアウトの設定。"""

    box_width: int = 13
    cell_width: int = 20
    cell_height: int = 6
    top_margin: int = 3


@dataclass
class Overlay:
    """色付き文字の描画情報。"""

    col: int
    text: str
    color: str


class Canvas:
    """ターミナルに表示する文字グリッドを管理する。"""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.grid: list[list[str]] = []
        self.overlays: dict[int, list[Overlay]] = {}
        self.clear()

    def clear(self) -> None:
        """描画領域を空白に戻す。"""
        self.grid = [
            [" " for _ in range(self.width)]
            for _ in range(self.height)
        ]
        self.overlays = {}

    def put(self, row: int, col: int, text: str) -> None:
        """指定位置へ文字列を書く。"""
        if not 0 <= row < self.height:
            return

        for offset, char in enumerate(text):
            target_col = col + offset

            if 0 <= target_col < self.width:
                self.grid[row][target_col] = char

    def add_overlay(
        self,
        row: int,
        col: int,
        text: str,
        color: str,
    ) -> None:
        """色付き文字を指定行へ登録する。"""
        if not color:
            return

        self.overlays.setdefault(row, []).append(
            Overlay(
                col=col,
                text=text,
                color=color,
            )
        )

    def rows(self) -> list[str]:
        """ANSIカラーを反映した表示用文字列を返す。"""
        result: list[str] = []

        for row_index, chars in enumerate(self.grid):
            line = "".join(chars).rstrip()

            overlays = self.overlays.get(row_index, [])

            # 後ろ側から色を差し込むことで、列位置がずれるのを防ぐ。
            for overlay in sorted(
                overlays,
                key=lambda item: item.col,
                reverse=True,
            ):
                line = (
                    line[:overlay.col]
                    + overlay.color
                    + overlay.text
                    + RESET
                    + line[overlay.col + len(overlay.text):]
                )

            result.append(line)

        return result


class TerminalRenderer:
    """Graphの状態をターミナル表示へ変換する。"""

    def __init__(
        self,
        graph: Graph,
        config: RenderConfig | None = None,
    ) -> None:
        self.graph = graph
        self.config = config or RenderConfig()

        self.zones = list(graph.zones.values())

        if not self.zones:
            raise ValueError("描画するZoneがありません")

        self._calculate_bounds()

        self.canvas = Canvas(
            self.width,
            self.height,
        )

    def _calculate_bounds(self) -> None:
        """Zone座標から描画範囲を計算する。"""
        self.min_x = min(zone.x for zone in self.zones)
        self.max_x = max(zone.x for zone in self.zones)
        self.min_y = min(zone.y for zone in self.zones)
        self.max_y = max(zone.y for zone in self.zones)

        self.width = (
            (self.max_x - self.min_x + 1)
            * self.config.cell_width
        )

        self.height = (
            (self.max_y - self.min_y + 1)
            * self.config.cell_height
            + self.config.top_margin * 2
        )

    def render(
        self,
        turn: int,
        moves: list[str],
    ) -> None:
        """1ターン分のフレームを描画する。"""
        self.canvas.clear()

        self._draw_connections()
        self._draw_zones()
        self._print_frame(turn, moves)

    def _center(
        self,
        zone_name: str,
    ) -> tuple[int, int]:
        """Zone中央の描画座標を返す。"""
        zone = self.graph.zones[zone_name]

        row = (
            self.config.top_margin
            + (self.max_y - zone.y) * self.config.cell_height
            + 2
        )

        col = (
            (zone.x - self.min_x) * self.config.cell_width
            + self.config.cell_width // 2
        )

        return row, col

    # ==========================
    # Connection
    # ==========================

    @staticmethod
    def _direction(
        start: int,
        end: int,
    ) -> int:
        """startからendへ進む方向を -1, 0, 1 で返す。"""
        if end > start:
            return 1

        if end < start:
            return -1

        return 0

    def _draw_segment(
        self,
        row_a: int,
        col_a: int,
        row_b: int,
        col_b: int,
        edge: str,
    ) -> None:
        """両端を除いて水平線または垂直線を描く。"""
        row_step = self._direction(row_a, row_b)
        col_step = self._direction(col_a, col_b)

        steps = max(
            abs(row_b - row_a),
            abs(col_b - col_a),
        )

        for step in range(1, steps):
            row = row_a + row_step * step
            col = col_a + col_step * step

            self._put_connection_character(
                row,
                col,
                edge,
            )

    def _put_connection_character(
        self,
        row: int,
        col: int,
        edge: str,
    ) -> None:
        """Connection罫線を描き、線が重なれば交差点にする。"""
        if not (
            0 <= row < self.canvas.height
            and 0 <= col < self.canvas.width
        ):
            return

        current = self.canvas.grid[row][col]

        if current == " ":
            self.canvas.grid[row][col] = edge
            return

        connection_edges = {"─", "│", "═", "║"}

        if current in connection_edges and current != edge:
            self.canvas.grid[row][col] = "┼"

    def _draw_connections(self) -> None:
        """すべてのConnectionを描画する。"""
        for connection in self.graph.connections:
            self._draw_connection(connection)

    def _draw_connection(
        self,
        connection: Connection,
    ) -> None:
        """Connectionを水平・垂直・L字のいずれかで描画する。"""
        start_row, start_col = self._center(connection.zone1)
        end_row, end_col = self._center(connection.zone2)

        if connection.has_explicit_capacity:
            horizontal_edge = "═"
            vertical_edge = "║"
        else:
            horizontal_edge = "─"
            vertical_edge = "│"

        if start_row == end_row:
            self._draw_segment(
                start_row,
                start_col,
                end_row,
                end_col,
                horizontal_edge,
            )

        elif start_col == end_col:
            self._draw_segment(
                start_row,
                start_col,
                end_row,
                end_col,
                vertical_edge,
            )

        else:
            self._draw_l_connection(
                start_row,
                start_col,
                end_row,
                end_col,
                horizontal_edge,
                vertical_edge,
                connection.has_explicit_capacity,
            )

        if connection.has_explicit_capacity:
            self._draw_capacity_label(
                connection,
                start_row,
                start_col,
                end_row,
                end_col,
            )

    def _draw_l_connection(
        self,
        start_row: int,
        start_col: int,
        end_row: int,
        end_col: int,
        horizontal_edge: str,
        vertical_edge: str,
        double: bool,
    ) -> None:
        """斜め位置のZoneを横→縦のL字で結ぶ。"""
        bend_row = start_row
        bend_col = end_col

        self._draw_segment(
            start_row,
            start_col,
            bend_row,
            bend_col,
            horizontal_edge,
        )

        self._draw_segment(
            bend_row,
            bend_col,
            end_row,
            end_col,
            vertical_edge,
        )

        corner = self._corner_character(
            moves_right=end_col > start_col,
            moves_down=end_row > start_row,
            double=double,
        )

        self._put_corner(
            bend_row,
            bend_col,
            corner,
        )

    def _put_corner(
        self,
        row: int,
        col: int,
        corner: str,
    ) -> None:
        """空白位置にだけL字の曲がり角を書く。"""
        if not (
            0 <= row < self.canvas.height
            and 0 <= col < self.canvas.width
        ):
            return

        if self.canvas.grid[row][col] == " ":
            self.canvas.grid[row][col] = corner

    @staticmethod
    def _corner_character(
        moves_right: bool,
        moves_down: bool,
        double: bool,
    ) -> str:
        """進行方向に対応するL字罫線を返す。"""
        if double:
            if moves_right and moves_down:
                return "╗"

            if moves_right:
                return "╝"

            if moves_down:
                return "╔"

            return "╚"

        if moves_right and moves_down:
            return "┐"

        if moves_right:
            return "┘"

        if moves_down:
            return "┌"

        return "└"

    def _draw_capacity_label(
        self,
        connection: Connection,
        start_row: int,
        start_col: int,
        end_row: int,
        end_col: int,
    ) -> None:
        """capacity付きConnectionの中央付近にラベルを書く。"""
        label = f"(cap:{connection.max_link_capacity})"

        middle_row = round(
            (start_row + end_row) / 2
        )
        middle_col = round(
            (start_col + end_col) / 2
        )

        label_row = middle_row - 3
        label_col = middle_col - len(label) // 2

        self.canvas.put(
            label_row,
            label_col,
            label,
        )

    # ==========================
    # Zone
    # ==========================

    def _box_characters(
        self,
        zone: Zone,
    ) -> tuple[str, str, str, str, str, str, str]:
        """Zoneの種類に応じた枠線文字を返す。"""
        if zone.name in (
            self.graph.start_zone_name,
            self.graph.end_zone_name,
        ):
            return "╔", "═", "╗", "║", "╚", "═", "╝"

        if zone.zone_type == "blocked":
            return "┌", "┄", "┐", "┆", "└", "┄", "┘"

        if zone.zone_type == "priority":
            return "╭", "─", "╮", "│", "╰", "─", "╯"

        if zone.zone_type == "restricted":
            return "┏", "━", "┓", "┃", "┗", "━", "┛"

        return "┌", "─", "┐", "│", "└", "─", "┘"

    def _draw_zone(
        self,
        zone: Zone,
    ) -> None:
        """Zone名・種類・occupancyを箱として描画する。"""
        row, col = self._center(zone.name)

        box_width = self.config.box_width

        left = col - box_width // 2
        top = row - 1

        (
            top_left,
            horizontal,
            top_right,
            vertical,
            bottom_left,
            bottom_horizontal,
            bottom_right,
        ) = self._box_characters(zone)

        capacity = (
            "∞"
            if zone.max_drones is None
            else str(zone.max_drones)
        )

        title = zone.name[:box_width].center(box_width)

        zone_type = (
            f"({zone.zone_type})"[:box_width]
            .center(box_width)
        )

        occupancy = self._occupancy_text(
            len(zone.occupants),
            capacity,
        ).center(box_width - 2)

        lines = (
            (top - 2, title),
            (top - 1, zone_type),
            (
                top,
                top_left
                + horizontal * (box_width - 2)
                + top_right,
            ),
            (
                top + 1,
                vertical
                + occupancy
                + vertical,
            ),
            (
                top + 2,
                bottom_left
                + bottom_horizontal * (box_width - 2)
                + bottom_right,
            ),
        )

        color = ZONE_COLORS.get(
            zone.color,
            "",
        )

        for line_row, text in lines:
            self.canvas.put(
                line_row,
                left,
                text,
            )

            self.canvas.add_overlay(
                line_row,
                left,
                text,
                color,
            )

    @staticmethod
    def _occupancy_text(
        drone_count: int,
        capacity: str,
    ) -> str:
        """ドローン数とZone容量を表示する文字列を作る。"""
        if drone_count == 0:
            return f"0/{capacity}"

        visible_markers = "▲" * min(
            drone_count,
            5,
        )

        overflow = (
            "…"
            if drone_count > 5
            else ""
        )

        return (
            f"{visible_markers}"
            f"{overflow} "
            f"{drone_count}/{capacity}"
        )

    def _draw_zones(self) -> None:
        """すべてのZoneを描画する。"""
        for zone in self.zones:
            self._draw_zone(zone)

    # ==========================
    # 出力
    # ==========================

    def _print_frame(
        self,
        turn: int,
        moves: list[str],
    ) -> None:
        """完成したCanvasをターミナルへ出力する。"""
        print(f"\n=== {turn}ターン目 ===")

        if moves:
            print(
                "移動:",
                " ".join(moves),
            )

        for line in self.canvas.rows():
            print(line)
