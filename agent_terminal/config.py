from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    tomllib = None  # type: ignore[assignment]


DEFAULT_MATE_HOME = Path.home() / ".mate"
DEFAULT_CONFIG = "config.toml"
DEFAULT_PROMPT = "prompt.md"
DEFAULT_KEYS = "keys.env"
DEFAULT_MCP = "mcp_servers.toml"
DEFAULT_DOTENV = ".env"


@dataclass
class ApprovalConfig:
    require_tools: set[str] = field(default_factory=lambda: {"run_command", "start_background_process"})
    allow_tools: set[str] = field(default_factory=set)
    require_commands: list[str] = field(default_factory=list)
    allow_commands: list[str] = field(default_factory=list)
    auto_approve: bool = False


@dataclass
class MateConfig:
    mate_home: Path
    raw: dict[str, Any] = field(default_factory=dict)
    approval: ApprovalConfig = field(default_factory=ApprovalConfig)
    prompt_override: str = ""


def mate_home() -> Path:
    configured = os.getenv("MATE_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    return DEFAULT_MATE_HOME.expanduser().resolve()


def ensure_mate_home(path: Path | None = None) -> Path:
    root = path or mate_home()
    root.mkdir(parents=True, exist_ok=True)
    return root


def load_config(path: Path | None = None) -> MateConfig:
    root = ensure_mate_home(path)
    raw = _load_toml(root / DEFAULT_CONFIG)
    approval = _load_approval(raw.get("approval", {}))
    prompt_override = _load_text(root / DEFAULT_PROMPT)
    _load_keys(root.parent / DEFAULT_DOTENV)
    _load_keys(root / DEFAULT_KEYS)
    return MateConfig(mate_home=root, raw=raw, approval=approval, prompt_override=prompt_override)


def tool_requires_approval(config: MateConfig, tool_name: str, command: str = "") -> bool:
    approval = config.approval
    if tool_allowed_without_approval(config, tool_name, command):
        return False
    if tool_name in approval.require_tools:
        return True
    if command and _matches_any(command, approval.require_commands):
        return True
    return False


def tool_allowed_without_approval(config: MateConfig, tool_name: str, command: str = "") -> bool:
    approval = config.approval
    return approval.auto_approve or tool_name in approval.allow_tools or bool(
        command and _matches_any(command, approval.allow_commands)
    )


def _load_approval(value: Any) -> ApprovalConfig:
    if not isinstance(value, dict):
        value = {}
    return ApprovalConfig(
        require_tools=set(_string_list(value.get("require_tools"), {"run_command", "start_background_process"})),
        allow_tools=set(_string_list(value.get("allow_tools"), set())),
        require_commands=_string_list(value.get("require_commands"), []),
        allow_commands=_string_list(value.get("allow_commands"), []),
        auto_approve=bool(value.get("auto_approve", False)),
    )


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if tomllib is None:
        return _load_simple_toml(path)
    with path.open("rb") as handle:
        loaded = tomllib.load(handle)
    return loaded if isinstance(loaded, dict) else {}


def _load_simple_toml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    section: dict[str, Any] = data
    pending_key = ""
    pending_items: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if pending_key:
            if line == "]":
                section[pending_key] = pending_items
                pending_key = ""
                pending_items = []
                continue
            pending_items.append(line.rstrip(",").strip().strip('"').strip("'"))
            continue
        if line.startswith("[") and line.endswith("]"):
            name = line.strip("[]").strip()
            section = data.setdefault(name, {})
            continue
        if "=" not in line:
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        if value == "[":
            pending_key = key
            pending_items = []
        elif value.lower() in {"true", "false"}:
            section[key] = value.lower() == "true"
        elif value.startswith("[") and value.endswith("]"):
            inner = value.strip("[]").strip()
            section[key] = [] if not inner else [item.strip().strip('"').strip("'") for item in inner.split(",")]
        else:
            section[key] = value.strip('"').strip("'")
    return data


def _load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _load_keys(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def _string_list(value: Any, default: Any) -> list[str]:
    if value is None:
        value = default
    if isinstance(value, str):
        return [value]
    if not isinstance(value, (list, tuple, set)):
        return list(default)
    return [str(item) for item in value if str(item).strip()]


def _matches_any(command: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(command, pattern) for pattern in patterns)
