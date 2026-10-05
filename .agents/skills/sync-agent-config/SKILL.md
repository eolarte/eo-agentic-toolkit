---
name: sync-agent-config
description: Sync canonical agent artifacts from .agents for GitHub Copilot and Codex. Use when Copilot agent files or MCP configuration must be replicated or validated.
user-invocable: true
argument-hint: "[--check | --sync | --validate] [--targets copilot,codex]"
---

# Sync Agent Config

Keep `.agents` as the only human-maintained source of truth for shared agent assets.

This skill supports GitHub Copilot and Codex only. It uses `scripts/sync_agent_configs.py` to:

- inspect `.agents/*.agent.md`
- inspect `.agents/skills/*`
- inspect `.agents/mcp.json`
- generate Copilot agent and MCP configuration from canonical `.agents` files
- report how Codex uses the canonical `.agents` tree without generating mirrors

## Workflow

1. Start with `--check`.
2. Review planned writes, conflicts, and degraded mappings.
3. Run `--sync` only after confirming the target set.
4. Finish with `--validate` to confirm generated Copilot files still match `.agents`.

## Rules

- `.agents` is the source of truth.
- Do not hand-edit generated target files.
- The sync script may overwrite only files it previously generated.
- If a conflicting unmanaged target file already exists, leave it in place and report it.
- Do not delete unmanaged mirrors automatically.

## Default target behavior

- `copilot`: generate `.github/agents/*` and `.vscode/mcp.json`; rely on `.agents/skills` directly
- `codex`: rely on root `AGENTS.md` and `.agents`; do not generate tool-specific mirrors

## Commands

Run from the repo root:

```bash
python3 .agents/skills/sync-agent-config/scripts/sync_agent_configs.py --check
python3 .agents/skills/sync-agent-config/scripts/sync_agent_configs.py --sync
python3 .agents/skills/sync-agent-config/scripts/sync_agent_configs.py --validate
python3 .agents/skills/sync-agent-config/scripts/sync_agent_configs.py --sync --targets copilot
```

## References

- Compatibility notes: `references/compatibility.md`
- Tests: `tests/test_sync_agent_configs.py`
