# Mate

Mate is a terminal coding companion for local projects. It talks to an
OpenAI-compatible API, works inside a bounded workspace, and shows a friendly TUI
with concise activity updates, approval prompts, colored diffs, and elapsed-time
results.

Mate keeps its behavior configurable through a repo-local `.mate` directory and
loads reusable commands, agents, hooks, and skills from `agent_resources`.

## Install

From the repo root, run the installer:

```bash
./install_agent.sh --api-key your-key --base-url https://api.openai.com/v1 --model gpt-4.1-mini
```

The installer creates `.venv`, installs Mate in editable mode, and saves model
settings to `.mate/keys.env`. Any missing value is read from the matching
environment variable first, then prompted interactively.

Supported installer options:

```bash
./install_agent.sh \
  --api-key your-key \
  --base-url https://api.openai.com/v1 \
  --model gpt-4.1-mini
```

Environment fallback names are `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and
`OPENAI_MODEL`. Environment variables already set in your shell take precedence
when Mate runs.

## Run

Use a specific workspace:

```bash
mate /path/to/workspace
```

or:

```bash
mate --workspace /path/to/workspace
```

If you omit the workspace, Mate creates a fresh temporary workspace under `/tmp`.

The bundled wrapper sets the repo-local config paths for you:

```bash
./run_agent.sh /path/to/workspace
./run_agent.sh
```

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

## Configuration

Mate loads configuration from `.mate` through `MATE_HOME`. The bundled
`run_agent.sh` sets `MATE_HOME` to the repo-local `.mate` directory.

```text
.mate/
  config.toml
  prompt.md
  mcp_servers.toml
  skills/
  keys.env.example
```

`.mate/config.toml` controls approval behavior and model environment variable
names:

```toml
[approval]
auto_approve = false
require_tools = ["run_command", "start_background_process"]
allow_tools = ["list_files", "glob_files", "read_file", "search_files"]
allow_commands = ["pwd", "ls", "ls *", "rg *", "git status*", "git diff*"]
require_commands = ["pip install *", "npm install*", "git push*"]

[model]
api_key_env = "OPENAI_API_KEY"
base_url_env = "OPENAI_BASE_URL"
model_env = "OPENAI_MODEL"
```

`.mate/prompt.md` is loaded as an extra system prompt at startup. Use it for
local behavior, conventions, and project preferences.

`.mate/keys.env` is for local secrets. It is ignored by git and loaded only when
the matching environment variable is not already set.

## Approvals

Mate asks before running tools or commands that match the approval config. The
approval prompt is transient, so after you answer the terminal keeps only a short
confirmation line:

```text
✔ You approved Mate to run `python -m pip install xgboost` this time
```

Read-only commands such as `ls`, `rg`, `git status`, and `git diff` can be
allowed in `.mate/config.toml`. Installs, servers, and mutating git commands
should usually remain approval-gated.

## MCP Servers

Put MCP server definitions in `.mate/mcp_servers.toml`. The file is currently the
canonical config location for Mate integrations and is shaped so a launcher can
start servers later without mixing connection details into prompts.

Example stdio server:

```toml
[servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/workspace"]
env = { LOG_LEVEL = "info" }
```

Example local service:

```toml
[servers.docs]
command = "python"
args = ["-m", "my_docs_mcp"]
cwd = "/path/to/docs-server"
env = { DOCS_ROOT = "/path/to/docs" }
```

Example remote HTTP server:

```toml
[servers.search]
url = "https://mcp.example.com"
headers = { Authorization = "Bearer ${SEARCH_MCP_TOKEN}" }
```

Store tokens in `.mate/keys.env` or your shell environment, not directly in
`mcp_servers.toml`.

## Skills

Put local skills in `.mate/skills`. Mate checks this folder before bundled
resources, so local skills can be added without editing `agent_resources`.

A skill is a directory containing a `SKILL.md` file:

```text
.mate/skills/my-skill/
  SKILL.md
  references/
  scripts/
```

Minimal local skill:

```markdown
# My Skill

Use this skill when Mate needs to handle a specific workflow.

1. Inspect the relevant files.
2. Apply the project convention.
3. Verify the result before answering.
```

Then restart Mate and ask it to use the skill by folder name, or list available
skills:

```text
/resources skills
```

Keep `SKILL.md` focused: describe when to use the skill, the workflow Mate should
follow, and which reference files matter. Put long examples, scripts, and
supporting docs in nearby `references/`, `examples/`, or `scripts/` folders.

Bundled skills still live under `agent_resources/mate-plugins` and are indexed in
`agent_resources/index/skills.txt`. Use that path for skills that should ship
with Mate releases.

## Project Layout

```text
agent_terminal/          Python package
agent_resources/         bundled commands, agents, hooks, and skills
.mate/                   local Mate config
scripts/                 release and installer scripts
run_agent.sh             local wrapper
install_agent.sh         local editable installer
```

## Release

From the repo root, build local release artifacts with:

```bash
scripts/release_github.sh
```

Publish a GitHub release with the GitHub CLI:

```bash
gh auth login
PUBLISH=1 scripts/release_github.sh
```

Or publish without `gh` by using a GitHub token:

```bash
GITHUB_TOKEN=ghp_xxx GITHUB_REPOSITORY=OWNER/REPO PUBLISH=1 scripts/release_github.sh
```

Optional release environment variables:

```bash
TAG=v0.1.0
RELEASE_TITLE="Mate v0.1.0"
NOTES_FILE=release-notes.md
```

Users can install Mate from a release tarball with:

```bash
bash install_mate.sh \
  --release-url https://github.com/OWNER/REPO/releases/download/v0.1.0/mate-0.1.0.tar.gz \
  --api-key your-key \
  --base-url https://api.openai.com/v1 \
  --model gpt-4.1-mini
```

The installer prompts for an OpenAI-compatible API key and base URL when they
are not provided. For non-interactive installs:

```bash
bash install_mate.sh \
  --release-url https://github.com/OWNER/REPO/releases/download/v0.1.0/mate-0.1.0.tar.gz \
  --api-key your-key \
  --base-url https://api.openai.com/v1 \
  --model gpt-4.1-mini
```

For local testing, install from a checked-out source folder:

```bash
bash scripts/install_mate.sh --source-dir /path/to/mate --api-key your-key --base-url https://api.openai.com/v1
```
