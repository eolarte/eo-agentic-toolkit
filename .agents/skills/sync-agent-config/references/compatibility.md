# Compatibility Matrix

This setup supports GitHub Copilot and Codex. `.agents` is the canonical source for shared skills and agent definitions.

## GitHub Copilot

- Agents: generated in `.github/agents/*.agent.md`
- Skills: discovered directly from `.agents/skills`
- MCP: generated in `.vscode/mcp.json` from `.agents/mcp.json`
- Repository instructions: maintained in `.github/copilot-instructions.md`

## Codex

- Guidance: root `AGENTS.md`
- Skills: discovered directly from `.agents/skills`
- Shared agent definitions: available in `.agents/*.agent.md` as repository guidance
- MCP: no repository-local Codex mirror is generated; configure Codex MCP separately if needed

## Sync safety

- Generated Markdown and JSON files carry a managed marker.
- The sync script overwrites only files it previously generated.
- Unmanaged target files are reported as conflicts and left unchanged.
