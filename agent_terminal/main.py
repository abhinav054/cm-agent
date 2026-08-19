from __future__ import annotations

import argparse
from pathlib import Path

from . import tools
from .server import AgentServer
from .ui import TerminalUI as UI

STEERING_PROMPTS: list[str] = []


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the terminal coding agent against a workspace directory.")
    parser.add_argument(
        "workspace_arg",
        nargs="?",
        help="Workspace directory the agent may read, write, and run commands inside.",
    )
    parser.add_argument(
        "--workspace",
        dest="workspace_option",
        help="Workspace directory the agent may read, write, and run commands inside.",
    )
    return parser.parse_args()


def _print_help() -> None:
    UI.panel(
        "Help",
        "Commands:\n"
        "- /help: show this help\n"
        "- /steer <guidance>: add persistent steering for future turns\n"
        "- /steer show: show active steering\n"
        "- /steer clear: clear active steering\n"
        "- /reset: clear conversation history except the base system prompt and steering\n"
        "- /resources [kind]: list copied resources; kind can be all, agents, skills, commands, hooks, plugins\n"
        "- /backgrounds: list background processes started in this session\n"
        "- exit or quit: close the agent\n"
        "\nShell commands and mutating Git commands require approval before they run.\n",
    )


def _steering_message() -> dict[str, str] | None:
    if not STEERING_PROMPTS:
        return None
    guidance = "\n".join(f"- {item}" for item in STEERING_PROMPTS)
    return {
        "role": "system",
        "content": (
            "Persistent user steering for this session. Follow this guidance when it does not conflict "
            f"with safety or the latest user request:\n{guidance}"
        ),
    }


def _handle_runtime_command(server: AgentServer, user_input: str) -> bool:
    if user_input == "/help":
        _print_help()
        return True
    if user_input == "/reset":
        server.reset(_steering_message())
        suffix = " Active steering was preserved." if STEERING_PROMPTS else ""
        UI.panel("Reset", f"Conversation reset.{suffix}", UI.CYAN)
        return True
    if user_input.startswith("/resources"):
        parts = user_input.split(maxsplit=1)
        kind = parts[1].strip() if len(parts) > 1 else "all"
        try:
            UI.panel("Resources", tools.list_agent_resources(kind), UI.CYAN)
        except Exception as exc:
            UI.panel("Resources", f"Could not list resources: {type(exc).__name__}: {exc}", UI.RED)
        return True
    if user_input == "/backgrounds":
        UI.panel("Background Processes", tools.list_background_processes(), UI.CYAN)
        return True
    if user_input == "/steer show":
        if not STEERING_PROMPTS:
            UI.panel("Steering", "No active steering prompts.", UI.CYAN)
        else:
            rows = [f"{index}. {prompt}" for index, prompt in enumerate(STEERING_PROMPTS, start=1)]
            UI.panel("Steering", "\n".join(rows), UI.CYAN)
        return True
    if user_input == "/steer clear":
        STEERING_PROMPTS.clear()
        UI.panel("Steering", "Cleared active steering prompts.", UI.CYAN)
        return True
    if user_input.startswith("/steer "):
        guidance = user_input.removeprefix("/steer ").strip()
        if not guidance:
            UI.panel("Steering", "Usage: /steer <guidance>", UI.YELLOW)
            return True
        STEERING_PROMPTS.append(guidance)
        server.messages.append(_steering_message())
        UI.panel("Steering", "Steering added for future turns.", UI.CYAN)
        return True
    return False


def main() -> None:
    args = _parse_args()
    workspace = args.workspace_option or args.workspace_arg or Path.cwd()
    server = AgentServer.create(workspace, UI)

    while True:
        try:
            user_input = input(UI.style("agent> ", UI.BOLD, UI.BLUE)).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue
        if _handle_runtime_command(server, user_input):
            continue

        answer = server.run_turn(user_input)
        UI.panel("Assistant", answer, UI.GREEN)


if __name__ == "__main__":
    main()
