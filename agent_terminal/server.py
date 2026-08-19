from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from . import tools


def _preview(value: str, limit: int = 900) -> str:
    value = value.strip()
    if not value:
        return "(no output)"
    return value if len(value) <= limit else value[:limit].rstrip() + "\n...[preview trimmed]"


def _json_arguments(value: str | None) -> dict[str, Any]:
    parsed = json.loads(value or "{}")
    if not isinstance(parsed, dict):
        raise ValueError("tool arguments must be a JSON object")
    return parsed


def describe_tool_start(name: str, arguments: dict[str, Any]) -> str:
    path = arguments.get("path")
    cwd = arguments.get("cwd", ".")
    if name == "browse_internet":
        return f"Fetch URL: {arguments.get('url', '(missing URL)')}"
    if name == "check_system_tools":
        return "Check local command-line tools"
    if name == "list_files":
        return f"List directory: {path or '.'}"
    if name == "glob_files":
        return f"Glob files: {arguments.get('pattern', '(missing pattern)')} in {cwd if path is None else path}"
    if name == "git":
        return f"Git: git {arguments.get('command', '(missing command)')}"
    if name == "read_file":
        return f"Read file: {path or '(missing path)'}"
    if name == "touch_file":
        return f"Touch file: {path or '(missing path)'}"
    if name == "write_file":
        action = "Append file" if arguments.get("append") else "Write file"
        return f"{action}: {path or '(missing path)'}"
    if name == "edit_file":
        return f"Edit file: {path or '(missing path)'}"
    if name == "run_command":
        return f"Shell: {arguments.get('command', '(missing command)')}  cwd={cwd}"
    if name == "start_background_process":
        return f"Start background: {arguments.get('command', '(missing command)')}  cwd={cwd}"
    if name == "read_background_process":
        return f"Read background output: {arguments.get('process_id', '(missing id)')}"
    if name == "stop_background_process":
        return f"Stop background process: {arguments.get('process_id', '(missing id)')}"
    if name == "list_background_processes":
        return "List background processes"
    if name == "request_user_input":
        return f"Ask user: {arguments.get('prompt', '(missing prompt)')}"
    if name == "record_workspace_server":
        return f"Record workspace server: {arguments.get('command', '(missing command)')}"
    if name == "search_files":
        return f"Search files: {arguments.get('query', '(missing query)')} in {arguments.get('path', '.')}"
    if name == "list_agent_resources":
        return f"List resources: {arguments.get('kind', 'all')}"
    if name == "read_agent_resource":
        return f"Read resource: {path or '(missing path)'}"
    if name == "load_command":
        return f"Load command: /{str(arguments.get('command_name', '')).lstrip('/')}"
    if name == "load_skill":
        return f"Load skill: {arguments.get('skill_name', '(missing skill)')}"
    if name == "load_agent_prompt":
        return f"Load agent prompt: {arguments.get('agent_name', '(missing agent)')}"
    if name == "update_todos":
        return "Update task list"
    if name == "run_plugin_hook":
        return f"Run plugin hook: {arguments.get('plugin_name', '(missing plugin)')}"
    return f"Tool: {name}"


def describe_tool_result(name: str, result: str, failed: bool) -> str:
    status = "Failed" if failed else "Done"
    preview = _preview(result)
    if name in {"read_file", "read_agent_resource", "load_command", "load_skill", "load_agent_prompt"}:
        return f"{status}. Loaded {len(result.splitlines())} line(s).\n{preview}"
    if name in {"list_files", "glob_files", "search_files", "list_agent_resources", "list_background_processes"}:
        count = 0 if result in {"", "no matches", "(empty)"} else len(result.splitlines())
        return f"{status}. {count} item(s).\n{preview}"
    if name == "request_user_input":
        return f"{status}. User input received."
    return f"{status}.\n{preview}"


def format_approval_request(name: str, arguments: dict[str, Any]) -> str:
    command = str(arguments.get("command", "")).strip()
    cwd = str(arguments.get("cwd", ".")).strip() or "."
    timeout = arguments.get("max_time_seconds")
    rows = [
        f"Tool: {name}",
        f"cwd: {cwd}",
        f"command: {command or '(missing command)'}",
    ]
    if timeout is not None:
        rows.append(f"max_time_seconds: {timeout}")
    return "\n".join(rows)


@dataclass
class AgentServer:
    client: OpenAI
    model: str
    ui: Any
    messages: list[dict[str, Any]]

    @classmethod
    def create(cls, workspace: str | os.PathLike[str], ui: Any) -> "AgentServer":
        workspace_path = tools.set_workspace(workspace)
        tools.set_tool_ui(
            diff_handler=ui.diff,
            input_handler=lambda prompt, secret, default: _input_with_ui(ui, prompt, secret, default),
        )

        api_key = os.getenv("OPENAI_API_KEY", "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")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
        model = os.getenv("OPENAI_MODEL", "openai/gpt-oss-120b")
        if not api_key:
            raise SystemExit("OPENAI_API_KEY is required")

        client = OpenAI(api_key=api_key, base_url=base_url)
        resource_root = tools.resource_root()
        base_system_message = {
            "role": "system",
            "content": (
                "You are a coding agent running in a terminal. "
                f"Your workspace is {workspace_path}. "
                f"Agent resources are available at {resource_root}. "
                "Use tools to inspect, search, create, and edit files. "
                "Do not write outside the workspace. "
                "At the start of every session, first understand the project structure from the supplied project structure context and inspect any additional files needed before planning changes. "
                "When browsing, use the browse_internet tool. "
                "Use list_agent_resources and read_agent_resource to discover and apply copied agents, skills, commands, hooks, and plugin guidance when relevant. "
                "Tool name mappings: LS=list_files, Glob=glob_files, Grep=search_files, Read=read_file, Write=write_file, Edit/MultiEdit=edit_file, Bash=run_command, TodoWrite=update_todos, Skill=load_skill, Task=load_agent_prompt, and slash commands=load_command. "
                "Use the git tool for Git status, diff, log, branch, show, add, commit, restore, and related operations instead of run_command. "
                "Use check_system_tools when a copied plugin depends on external CLIs. "
                "When you start or identify a workspace server, record it with record_workspace_server; run_command also records common server commands automatically in .codex/workspace-servers.jsonl. "
                "Use start_background_process for long-running servers or watchers, then list_background_processes, read_background_process, and stop_background_process to manage them. "
                "Whenever required information is missing from the user, such as database URLs, API keys, credentials, tokens, deployment settings, or important product choices, use request_user_input to ask for it in the terminal UI, then proceed with the answer or implementation. Use secret=true for sensitive values. "
                "Before changing files, inspect relevant files when they exist. "
                "Use run_command for tests, formatting, and project inspection. "
                "After writing code, summarize the changed files and the verification you performed."
            ),
        }
        project_context = tools.project_structure_summary()
        project_message = {
            "role": "system",
            "content": (
                "Project structure context captured at startup. Use this to orient yourself before "
                f"answering the first user request:\n{project_context}"
            ),
        }
        ui.panel(
            "Agent Terminal",
            f"Workspace: {workspace_path}\nResources: {resource_root}\nModel: {model}\n\n"
            "Type a request, /help for commands, or exit/quit to close.",
            ui.BLUE,
        )
        ui.panel("Project Structure", project_context, ui.CYAN)
        return cls(client=client, model=model, ui=ui, messages=[base_system_message, project_message])

    def reset(self, steering_message: dict[str, str] | None = None) -> None:
        base = self.messages[0]
        project_context = tools.project_structure_summary()
        project = {
            "role": "system",
            "content": (
                "Project structure context captured at reset. Use this to orient yourself before "
                f"answering the next user request:\n{project_context}"
            ),
        }
        self.messages = [base, project] + ([steering_message] if steering_message else [])

    def run_turn(self, user_goal: str) -> str:
        self.messages.append({"role": "user", "content": user_goal})
        return self._run_agent_turn(user_goal)

    def _tool_message(self, tool_call: Any) -> dict[str, Any]:
        name = tool_call.function.name
        failed = False
        try:
            arguments = _json_arguments(tool_call.function.arguments)
            self.ui.status("Tool", describe_tool_start(name, arguments), self.ui.MAGENTA)
            requires_approval = name in tools.APPROVAL_REQUIRED_TOOLS or (
                name == "git" and tools.git_requires_approval(str(arguments.get("command", "")))
            )
            if requires_approval and not self._confirm_tool_execution(name, arguments):
                raise PermissionError("user denied command approval")
            result = tools.TOOLS[name](**arguments)
        except Exception as exc:
            failed = True
            result = f"ERROR: {type(exc).__name__}: {exc}"
            self.ui.status("Tool", name, self.ui.RED)

        human_summary = describe_tool_result(name, str(result), failed)
        self.ui.panel("Tool Result", human_summary, self.ui.RED if failed else self.ui.GREEN)
        return {"role": "tool", "tool_call_id": tool_call.id, "content": str(result)}

    def _confirm_tool_execution(self, name: str, arguments: dict[str, Any]) -> bool:
        if os.getenv("AGENT_AUTO_APPROVE_COMMANDS", "").lower() in {"1", "true", "yes"}:
            return True
        self.ui.panel("Approval Required", format_approval_request(name, arguments), self.ui.YELLOW)
        while True:
            answer = self.ui.prompt("Approve command? [y/N] ").strip().lower()
            if answer in {"y", "yes"}:
                return True
            if answer in {"", "n", "no"}:
                return False

    def _run_agent_until_answer(self) -> str:
        while True:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=tools.TOOL_DEFINITIONS,
                tool_choice="auto",
            )
            message = response.choices[0].message
            self.messages.append(message.model_dump(exclude_none=True))

            if not message.tool_calls:
                return message.content or ""

            for tool_call in message.tool_calls:
                self.messages.append(self._tool_message(tool_call))

    def _run_agent_turn(self, user_goal: str) -> str:
        max_checks = max(0, int(os.getenv("AGENT_HARNESS_MAX_RETRIES", "2")))
        for check_number in range(max_checks + 1):
            answer = self._run_agent_until_answer()
            if check_number >= max_checks:
                return answer

            try:
                assessment = self._assess_answer(user_goal, answer)
            except Exception as exc:
                self.ui.panel("Harness", f"Skipped response check ({type(exc).__name__}: {exc})", self.ui.YELLOW)
                return answer

            aligned = bool(assessment.get("aligned"))
            can_improve = bool(assessment.get("can_improve_with_tools"))
            reason = str(assessment.get("reason", "")).strip()
            follow_up = str(assessment.get("follow_up_prompt", "")).strip()
            if aligned:
                if reason:
                    self.ui.panel("Harness", f"Response looks aligned. {reason}", self.ui.CYAN)
                return answer
            if not can_improve or not follow_up:
                if reason:
                    self.ui.panel("Harness", f"Response may be incomplete. {reason}", self.ui.YELLOW)
                return answer

            self.ui.panel("Harness", f"Asking the agent for another pass. {reason}", self.ui.YELLOW)
            self.messages.append(
                {
                    "role": "user",
                    "content": (
                        "Quality harness feedback: your previous answer may not fully satisfy the user. "
                        "Use any relevant tools and improve the answer. "
                        f"Reason: {reason}\nFollow-up instruction: {follow_up}"
                    ),
                }
            )

        return answer

    def _assess_answer(self, user_goal: str, answer: str) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict production QA harness for a terminal coding agent. "
                        "Decide whether the assistant's response satisfies the user's latest prompt. "
                        "If it falls short and tools or more inspection could help, request another pass. "
                        "Return only JSON with keys: aligned (boolean), can_improve_with_tools (boolean), "
                        "reason (short string), follow_up_prompt (string)."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"User prompt:\n{user_goal}\n\n"
                        f"Assistant response:\n{answer}\n\n"
                        "Assess whether the response is complete, directly responsive, and honest about verification."
                    ),
                },
            ],
            response_format={"type": "json_object"},
        )
        return _extract_json_object(response.choices[0].message.content or "{}")


def _extract_json_object(value: str) -> dict[str, Any]:
    text = value.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found")
    parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("assessment was not a JSON object")
    return parsed


def _input_with_ui(ui: Any, prompt: str, secret: bool, default: str | None) -> str:
    rows = [prompt.strip() or "Input required"]
    if default is not None and not secret:
        rows.append(f"Default: {default}")
    ui.panel("Input Required", "\n".join(rows), ui.YELLOW)
    return ui.prompt("Enter value: ", secret=secret)
