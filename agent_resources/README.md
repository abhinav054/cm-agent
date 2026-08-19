# Agent Resources

This directory contains Mate resources copied into a coding-agent-friendly layout.

- `mate-plugins/` is a faithful copy of the source `plugins/` tree.
- `index/agents.txt` lists available sub-agent prompts.
- `index/skills.txt` lists available `SKILL.md` files.
- `index/commands.txt` lists available command prompts.
- `index/hooks.txt` lists available hook manifests.

The terminal agent can discover these with `list_agent_resources` and read any file with
`read_agent_resource`, using paths relative to this directory.
