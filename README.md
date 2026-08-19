# Mate

Mate is a small Python terminal coding companion that talks to an OpenAI-compatible API and can:

- browse the internet with `curl`
- list files
- glob files
- read files
- touch files
- write files
- edit files
- run workspace shell commands with terminal approval
- run constrained Git operations with approval for mutating commands
- start, inspect, and stop background processes for dev servers and watchers
- ask for required user input in the terminal TUI, including hidden prompts for secrets
- record workspace server launch commands for service creation
- search files
- load copied commands, agents, skills, and hooks
- check its final answer with a bounded result check before returning it

Mate only reads, writes, and runs workspace commands inside the workspace
directory you pass on startup.

On startup, Mate captures and displays a project structure summary
for the selected workspace, then includes that context in the model prompt so it
orients itself before acting.

## Architecture

- `agent_terminal/main.py`: terminal client, runtime commands, and input loop
- `agent_terminal/server.py`: model loop, tool-call execution, approval routing, and result checking
- `agent_terminal/tools.py`: workspace-safe tools, schemas, Git, files, commands, resources, and background processes
- `agent_terminal/ui.py`: terminal panels, colors, prompts, and colored file diffs

## Setup

```bash
cd agent_terminal
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Configure an OpenAI-compatible endpoint:

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4.1-mini"
```

For compatible local servers, change `OPENAI_BASE_URL` and `OPENAI_MODEL`.

## Workspace Servers

When Mate runs a common long-running server command, such as `npm run dev`,
`python -m http.server`, `uvicorn ...`, or `go run ...`, it appends a JSON line
to `.codex/workspace-servers.jsonl` in the active workspace. Each record includes
the workspace path, relative cwd, command, timestamp, and reason, so a separate
service manager can create or reconcile a service for that server.

## Command Approval and Background Processes

The terminal UI shows friendly activity updates while Mate works, including
elapsed time for model and tool work. Tool output is sent back to the model but
the shell shows concise status lines such as `Ran shell command`, `Read file`,
or `Edited file` instead of raw tool-result dumps.

When Mate asks to use `run_command`, `start_background_process`, or a
mutating Git command, the terminal shows an approval panel with the command, cwd,
and timeout. Approve with `y`/`yes`, or press Enter to deny. Set
`AGENT_AUTO_APPROVE_COMMANDS=1` only for trusted local sessions where you do not
want the prompt.

Read-only Git commands such as `status`, `diff`, `log`, `branch`, and `show` run
through the `git` tool without shell execution. Mutating commands such as `add`,
`commit`, `restore`, `checkout`, `reset`, `push`, and `pull` require approval.

Long-running commands should use `start_background_process` instead of
`run_command`. Mate can then call `list_background_processes`,
`read_background_process`, and `stop_background_process`. You can also type
`/backgrounds` to see processes started in the current terminal session.

When Mate needs information that is not available in the workspace, such as
database URLs, API keys, credentials, tokens, or deployment settings, it should
use `request_user_input`. Sensitive values are requested with hidden terminal
input so they are not echoed on screen.

## Run

```bash
mate /path/to/the/folder/you/want/mate/to-edit
```

You can also use `mate --workspace /path/to/workspace`.
If you omit the workspace, `mate` creates a new temporary workspace
directory under `/tmp`.

Type requests such as:

```text
Create a Python file named app.py that prints hello.
Search for TODO comments.
Browse https://example.com and summarize it.
```

Use `exit` or `quit` to close Mate.

## Runtime Commands

Inside Mate:

```text
/help
/steer Prefer small, focused patches and always run tests before final answers.
/steer show
/steer clear
/resources all
/resources skills
/backgrounds
/reset
```

`/steer` adds persistent guidance for later turns. `/reset` clears the conversation
history while preserving active steering prompts.

The result check runs after each response. If the response does not
appear aligned with the latest prompt and more tool work could help, it asks the
Mate to take another pass with that feedback. Control retries with:

```bash
export AGENT_HARNESS_MAX_RETRIES=2
```
