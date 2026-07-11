from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

from openai import OpenAI


MAX_TOOL_OUTPUT_CHARS = 16_000


def _workspace() -> Path:
    return Path.cwd().resolve()


def _resolve_in_workspace(path: str | None) -> Path:
    root = _workspace()
    target = root if not path else (root / path).resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"path escapes workspace: {path}")
    return target


def _trim_output(value: str) -> str:
    if len(value) <= MAX_TOOL_OUTPUT_CHARS:
        return value
    return value[:MAX_TOOL_OUTPUT_CHARS] + "\n...[trimmed]"


def browse_internet(url: str, max_time_seconds: int = 20) -> str:
    """Fetch a URL using curl and return response text."""
    if not url.startswith(("http://", "https://")):
        raise ValueError("url must start with http:// or https://")

    timeout = max(1, min(int(max_time_seconds), 60))
    result = subprocess.run(
        [
            "curl",
            "--location",
            "--silent",
            "--show-error",
            "--max-time",
            str(timeout),
            url,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout if result.stdout else result.stderr
    return _trim_output(output)


def list_files(path: str = ".") -> str:
    """List files under a workspace path."""
    target = _resolve_in_workspace(path)
    if not target.exists():
        raise FileNotFoundError(f"path does not exist: {path}")

    if target.is_file():
        return str(target.relative_to(_workspace()))

    rows: list[str] = []
    for child in sorted(target.iterdir(), key=lambda item: (item.is_file(), item.name.lower())):
        suffix = "/" if child.is_dir() else ""
        rows.append(f"{child.relative_to(_workspace())}{suffix}")
    return "\n".join(rows) if rows else "(empty)"


def touch_file(path: str) -> str:
    """Create a file or update its modified timestamp inside the workspace."""
    target = _resolve_in_workspace(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.touch()
    return f"touched {target.relative_to(_workspace())}"


def write_file(path: str, content: str, append: bool = False) -> str:
    """Write or append text to a file inside the workspace."""
    target = _resolve_in_workspace(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with target.open(mode, encoding="utf-8") as file:
        file.write(content)
    action = "appended to" if append else "wrote"
    return f"{action} {target.relative_to(_workspace())}"


def search_files(query: str, path: str = ".") -> str:
    """Search file names and text content inside the workspace."""
    target = _resolve_in_workspace(path)
    if not target.exists():
        raise FileNotFoundError(f"path does not exist: {path}")

    command = ["rg", "--line-number", "--hidden", "--glob", "!.git", query, str(target)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return _search_files_without_rg(query, target)
    if result.returncode == 0:
        return _trim_output(result.stdout)
    if result.returncode == 1:
        return "no matches"

    fallback = _search_files_without_rg(query, target)
    return fallback if fallback else _trim_output(result.stderr)


def _search_files_without_rg(query: str, target: Path) -> str:
    matches: list[str] = []
    files = [target] if target.is_file() else [item for item in target.rglob("*") if item.is_file()]
    for file_path in files:
        if ".git" in file_path.parts:
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if query in line:
                relative = file_path.relative_to(_workspace())
                matches.append(f"{relative}:{line_number}:{line}")
    return _trim_output("\n".join(matches)) if matches else "no matches"


TOOLS: dict[str, Callable[..., str]] = {
    "browse_internet": browse_internet,
    "list_files": list_files,
    "touch_file": touch_file,
    "write_file": write_file,
    "search_files": search_files,
}


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "browse_internet",
            "description": "Browse the internet by fetching a URL with curl.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "HTTP or HTTPS URL to fetch."},
                    "max_time_seconds": {
                        "type": "integer",
                        "description": "Curl timeout between 1 and 60 seconds.",
                        "default": 20,
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a folder under the current workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to list.", "default": "."}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "touch_file",
            "description": "Create a file or update its modified timestamp.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Relative file path."}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or append text to a file in the current workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path."},
                    "content": {"type": "string", "description": "Text content to write."},
                    "append": {
                        "type": "boolean",
                        "description": "Append instead of overwriting when true.",
                        "default": False,
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search file contents with ripgrep, falling back to Python search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text or regex query to search for."},
                    "path": {"type": "string", "description": "Relative path to search.", "default": "."},
                },
                "required": ["query"],
            },
        },
    },
]


def _tool_message(tool_call: Any) -> dict[str, Any]:
    name = tool_call.function.name
    try:
        arguments = json.loads(tool_call.function.arguments or "{}")
        result = TOOLS[name](**arguments)
    except Exception as exc:
        result = f"ERROR: {type(exc).__name__}: {exc}"

    return {
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": str(result),
    }


def _run_agent_turn(client: OpenAI, model: str, messages: list[dict[str, Any]]) -> str:
    while True:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))

        if not message.tool_calls:
            return message.content or ""

        for tool_call in message.tool_calls:
            tool_response = _tool_message(tool_call)
            messages.append(tool_response)
            print(f"\n[tool:{tool_call.function.name}]\n{tool_response['content']}\n")


def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY","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")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
    model = os.getenv("OPENAI_MODEL", "openai/gpt-oss-120b")

    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required")

    client = OpenAI(api_key=api_key, base_url=base_url)
    workspace = _workspace()
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are a coding agent running in a terminal. "
                f"Your workspace is {workspace}. "
                "Use tools to inspect, search, create, and edit files. "
                "Do not write outside the workspace. "
                "When browsing, use the browse_internet tool. "
                "Before changing files, inspect relevant files when they exist. "
                "After writing code, summarize the changed files and suggest any command the user should run."
            ),
        }
    ]

    print(f"Agent terminal opened in: {workspace}")
    print("Type a request, or use 'exit'/'quit' to close.\n")

    while True:
        try:
            user_input = input("agent> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})
        answer = _run_agent_turn(client, model, messages)
        print(f"\n{answer}\n")


if __name__ == "__main__":
    main()
