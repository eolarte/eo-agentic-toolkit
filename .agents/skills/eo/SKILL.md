---
name: eo
description: Use the named eo- subagents to carry out a task when the user asks for the EO agent workflow or invokes $eo.
---

# EO subagent workflow

Apply the EO delegation workflow to the task accompanying this invocation, or to the active task if no new task is supplied. If neither exists, ask what task to perform. This invocation requests actual delegation to the available named `eo-` agents.

Follow the applicable `AGENTS.md` and use the registered custom agent types by their exact names. Do not substitute a generic agent with an EO name in its prompt. If the required custom agent type or delegation tool is unavailable, explain the limitation before offering a fallback; do not claim delegation occurred.

## Routing

- `eo-king`: architecture, task decomposition, coordination, and integration for work spanning components or requiring architectural decisions.
- `eo-scout`: read-only discovery of relevant code, existing patterns, dependencies, and validation before substantial implementation.
- `eo-archer-csharp`: C# and .NET implementation and targeted validation.
- `eo-archer-python`: Python implementation and targeted validation.
- `eo-archer-sql`: SQL, schema, migration, and data correctness work.
- `eo-wonder-builder`: UI/UX design, accessible states, and implementation handoff.
- `eo-villager`: bounded, low-risk edits and supporting work.
- `eo-monk`: independent review after delegated implementation and before completion.

Choose the smallest useful set of agents. A small task explicitly submitted through this skill can go directly to `eo-villager`; do not spawn every role. For substantial implementation, obtain Scout's findings first, then delegate bounded implementation to the relevant specialist. Use King when coordination or architecture warrants it. After delegated implementation, obtain Monk's review, resolve actionable findings, and run the affected component's existing checks.

Give each agent a concrete objective, owned paths or responsibilities, relevant constraints, expected validation, and a stopping point. Tell agents making edits that they share the workspace, must preserve others' changes, and must accommodate concurrent work. Parallelize only independent responsibilities; do not duplicate investigations or edits. Retain responsibility for integration and final verification.

Report changes, validation actually performed, unresolved risks, and any decisions requiring user input. The invocation applies to the current task; it does not change global configuration or authorize unrelated actions.
