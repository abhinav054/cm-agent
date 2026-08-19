# Runtime Notes

The copied Mate resources are available to the terminal agent, but Mate
tool names are mapped onto local Python tools.

## Local Tool Equivalents

- `LS` -> `list_files`
- `Glob` -> `glob_files`
- `Grep` -> `search_files`
- `Read` -> `read_file`
- `Write` -> `write_file`
- `Edit` / `MultiEdit` -> `edit_file`
- `Bash` -> `run_command`
- `TodoWrite` -> `update_todos`
- `Skill` -> `load_skill`
- `Task` -> `load_agent_prompt`
- Slash commands -> `load_command`
- Plugin hooks -> `run_plugin_hook`
- WebFetch / WebSearch -> `browse_internet` or direct package/registry checks through `run_command`

## External Commands

Required for core operation:

- `bash`
- `python3`
- `git`
- `rg`
- `curl`

Optional or plugin-specific:

- `gh`: needed by GitHub PR review and PR creation/comment commands
- `jq`: needed by Ralph Wiggum transcript parsing
- `node`, `npm`, `npx`: needed by TypeScript Agent SDK workflows
- `perl`, `sed`, `awk`: used by some shell hooks/scripts

Use the agent tool `check_system_tools` to check the current machine.
