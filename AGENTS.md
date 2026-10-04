# Agent setup

This repository keeps reusable agent assets in `.agents`.

- Skills live in `.agents/skills/<skill-name>/SKILL.md`; read the selected skill and its referenced resources before following its workflow.
- Shared agent definitions live in `.agents/*.agent.md`, including the
  `eo-*` architecture, implementation, discovery, quality, and design agents.
- GitHub Copilot uses the shared skills in `.agents/skills`, its repository instructions in `.github/copilot-instructions.md`, and native agent definitions in `.github/agents`.
- MCP server definitions are maintained in `.agents/mcp.json`; `.vscode/mcp.json` provides the VS Code Copilot configuration.

## EO agent workflow

- Use `eo-king` for architecture, delegation, integration, and final delivery.
- Use `eo-scout` for read-only discovery before implementation.
- Use `eo-archer-csharp`, `eo-archer-python`, or `eo-archer-sql` for bounded
  implementation work in their respective domains.
- Use `eo-villager` for small, low-risk tasks and `eo-wonder-builder` for UI/UX
  work.
- Require `eo-monk` as an independent quality gate after delegated
  implementation.

Codex uses this root `AGENTS.md` together with the canonical `.agents` tree.
GitHub Copilot uses the generated `.github/agents` mirrors and the same
canonical skills and instructions.

Keep `.agents` as the canonical source for shared skills and agent definitions. When updating a Copilot agent definition, keep its `.github/agents` counterpart in sync.
