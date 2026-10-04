# Copilot Instructions

## Core principles
- Keep changes small, focused, and easy to review.
- Prefer the simplest solution that matches existing project patterns.
- Preserve current behavior unless a change is explicitly requested.

## Code quality
- Follow existing style, naming, and architecture in nearby files.
- Add clear error handling and input validation where needed.
- Avoid introducing unnecessary dependencies or abstractions.

## Tests and validation
- Add or update tests for behavior changes and bug fixes.
- Run relevant tests and checks before finishing.
- If you cannot run validation locally, state that clearly.

## Collaboration
- Explain what changed and why in concise terms.
- Call out assumptions, risks, and follow-up work when relevant.
- Keep documentation in sync when public behavior or usage changes.

## Agent configuration
- Treat `.agents` as the canonical source for shared agent definitions and
  skills.
- Use the `eo-*` agents for their documented bounded roles; use `eo-king` for
  coordination and `eo-monk` for the independent quality gate.
- Keep `.github/agents` mirrors synchronized through
  `.agents/skills/sync-agent-config`; do not hand-edit generated mirrors.
- The same root `AGENTS.md` and canonical `.agents` tree are used by Codex.
