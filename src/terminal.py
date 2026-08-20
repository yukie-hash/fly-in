from typing import Optional

COLOR_CODES = {
    "black": "\033[30m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "blue": "\033[94m",
    "gray": "\033[90m",
    "white": "\033[97m",
    "cyan": "\033[96m",
    "purple": "\033[95m",
    "violet": "\033[38;5;141m",
    "crimson": "\033[38;5;197m",
    "lime": "\033[92m",
    "orange": "\033[38;5;208m",
    "brown": "\033[38;5;130m",
    "maroon": "\033[38;5;52m",
    "darkred": "\033[38;5;88m",
    "gold": "\033[38;5;220m",
}
RESET_CODE = "\033[0m"
RAINBOW_CODES = (
    "\033[91m",  # red
    "\033[93m",  # yellow
    "\033[92m",  # green
    "\033[96m",  # cyan
    "\033[94m",  # blue
    "\033[95m",  # purple
)


class TerminalColorizer():
    def colorize(self, text: str, color_name: Optional[str]) -> str:
        if color_name == "rainbow":
            return "".join(
                f"{RAINBOW_CODES[index % len(RAINBOW_CODES)]}{character}"
                for index, character in enumerate(text)
            ) + RESET_CODE
        if color_name is None or color_name not in COLOR_CODES:
            return text
        return f"{COLOR_CODES[color_name]}{text}{RESET_CODE}"
