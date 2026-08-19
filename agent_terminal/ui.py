from __future__ import annotations

import os
import shutil


class TerminalUI:
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    MAGENTA = "\033[35m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @staticmethod
    def enabled() -> bool:
        return os.getenv("NO_COLOR") is None

    @classmethod
    def style(cls, value: str, *codes: str) -> str:
        if not cls.enabled():
            return value
        return "".join(codes) + value + cls.RESET

    @classmethod
    def rule(cls, title: str = "") -> None:
        width = min(shutil.get_terminal_size((88, 20)).columns, 100)
        if title:
            label = f" {title} "
            left = max(2, (width - len(label)) // 2)
            right = max(2, width - left - len(label))
            print(cls.style("─" * left + label + "─" * right, cls.DIM))
        else:
            print(cls.style("─" * width, cls.DIM))

    @classmethod
    def panel(cls, title: str, body: str, color: str = CYAN) -> None:
        cls.rule(cls.style(title, cls.BOLD, color))
        print(body.rstrip() if body.strip() else "(no output)")
        cls.rule()
        print()

    @classmethod
    def status(cls, label: str, body: str = "", color: str = CYAN) -> None:
        prefix = cls.style(f"{label}:", cls.BOLD, color)
        print(f"\n{prefix} {body}".rstrip())

    @classmethod
    def diff(cls, body: str) -> None:
        cls.rule(cls.style("File Diff", cls.BOLD, cls.MAGENTA))
        for line in body.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                print(cls.style(line, cls.GREEN))
            elif line.startswith("-") and not line.startswith("---"):
                print(cls.style(line, cls.RED))
            elif line.startswith("@@"):
                print(cls.style(line, cls.CYAN, cls.BOLD))
            elif line.startswith(("---", "+++")):
                print(cls.style(line, cls.YELLOW))
            else:
                print(line)
        cls.rule()
        print()

    @classmethod
    def prompt(cls, label: str, secret: bool = False) -> str:
        if secret:
            import getpass

            return getpass.getpass(cls.style(label, cls.BOLD, cls.YELLOW))
        return input(cls.style(label, cls.BOLD, cls.YELLOW))
