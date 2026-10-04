---
name: sync-agent-config
description: Sync canonical agent artifacts from .agents into tool-specific folders for Claude, Cursor, GitHub Copilot, OpenCode, Codex, and Factory Droid. Use when agent configs, skills, or MCP server definitions must be replicated or validated across coding tools.
user-invocable: true
argument-hint: "[--check | --sync | --validate] [--targets claude,cursor,copilot,opencode,codex,droid]"
---

# Sync Agent Config

Keep `.agents` as the only human-maintained source of truth for shared agent assets.

This skill uses `scripts/sync_agent_configs.py` to:

- inspect `.agents/*.agent.md`
- inspect `.agents/skills/*`
- inspect `.agents/mcp.json`
- generate tool-specific wrappers or copies where required
- report unsupported or degraded mappings instead of inventing fake support

## Workflow

1. Start with `--check`.
2. Review planned writes, conflicts, and degraded mappings.
3. Run `--sync` only after confirming the target set.
4. Finish with `--validate` to confirm generated files still match `.agents`.

## Rules

- `.agents` is the source of truth.
- Do not hand-edit generated target files.
- The sync script may overwrite only files it previously generated.
- If a conflicting unmanaged target file already exists, leave it in place and report it.
- Do not delete unmanaged mirrors automatically.

## Default target behavior

- `claude`: generate `.claude/agents/*`, `.claude/skills/*`, and project `.mcp.json`
- `cursor`: generate `.cursor/rules/agents-and-skills-index.mdc` and `.cursor/mcp.json`
- `copilot`: generate `.github/agents/*` and `.vscode/mcp.json`; rely on `.agents/skills` directly
- `opencode`: generate `.opencode/agents/*` and `opencode.jsonc`; rely on `.agents/skills` directly
- `codex`: rely on root `AGENTS.md` and `.agents`; no repo-local mirror by default
- `droid`: generate `.factory/droids/*`, `.factory/skills/*`, and `.factory/mcp.json`

## Commands

Run from the repo root:

```bash
python3 .agents/skills/sync-agent-config/scripts/sync_agent_configs.py --check
python3 .agents/skills/sync-agent-config/scripts/sync_agent_configs.py --sync
python3 .agents/skills/sync-agent-config/scripts/sync_agent_configs.py --validate
python3 .agents/skills/sync-agent-config/scripts/sync_agent_configs.py --sync --targets claude,cursor
```

## References

- Compatibility notes: `references/compatibility.md`
- Tests: `tests/test_sync_agent_configs.py`
