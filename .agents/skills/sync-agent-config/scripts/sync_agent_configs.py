#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
SOURCE_ROOT = ROOT / ".agents"
SOURCE_SKILLS = SOURCE_ROOT / "skills"
SOURCE_MCP = SOURCE_ROOT / "mcp.json"
SOURCE_AGENTS_GLOB = "*.agent.md"

TARGETS = ("copilot", "codex")
JSON_MANAGED_KEY = "x-sync-agent-config"
MANAGED_MARKER = "Managed by sync-agent-config"
HEADER_TEMPLATE = (
    "<!-- Managed by sync-agent-config; target={target}; source={source}; "
    "mode=generated; regenerate=python3 .agents/skills/sync-agent-config/scripts/"
    "sync_agent_configs.py --sync -->\n"
)


@dataclass
class Operation:
    target: str
    category: str
    source: Path | None
    destination: Path | None
    kind: str
    status: str
    note: str = ""
    content: str | None = None
    json_data: dict[str, Any] | None = None


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def ensure_source_tree() -> None:
    if not SOURCE_ROOT.is_dir():
        fail("missing .agents source directory")
    if not SOURCE_SKILLS.is_dir():
        fail("missing .agents/skills source directory")
    if not SOURCE_MCP.is_file():
        fail("missing .agents/mcp.json")


def source_agents() -> list[Path]:
    return sorted(SOURCE_ROOT.glob(SOURCE_AGENTS_GLOB))


def source_skill_dirs() -> list[Path]:
    skill_dirs = []
    for path in sorted(SOURCE_SKILLS.iterdir()):
        if path.is_dir() and (path / "SKILL.md").is_file():
            skill_dirs.append(path)
    return skill_dirs


def relative_to_root(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def build_header(target: str, source: Path) -> str:
    return HEADER_TEMPLATE.format(target=target, source=relative_to_root(source))


def is_managed_markdown(path: Path) -> bool:
    if not path.exists():
        return False
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return False
    return any(MANAGED_MARKER in line for line in lines[:12])


def read_json_like(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue
        lines.append(line)
    return json.loads("\n".join(lines) if lines else "{}")


def is_managed_json(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        data = read_json_like(path)
    except Exception:
        return False
    return isinstance(data, dict) and JSON_MANAGED_KEY in data


def make_markdown_copy_operation(target: str, category: str, source: Path, destination: Path) -> Operation:
    body = source.read_text(encoding="utf-8")
    content = build_header(target, source) + body
    if destination.exists() and not is_managed_markdown(destination):
        return Operation(target, category, source, destination, "markdown", "conflict", "unmanaged target exists")
    return Operation(target, category, source, destination, "markdown", "planned", content=content)


def mcp_source_json() -> dict[str, Any]:
    return json.loads(SOURCE_MCP.read_text(encoding="utf-8"))


def build_managed_json(target: str, payload: dict[str, Any], source: Path) -> dict[str, Any]:
    return {
        JSON_MANAGED_KEY: {
            "target": target,
            "source": relative_to_root(source),
            "regenerate": "python3 .agents/skills/sync-agent-config/scripts/sync_agent_configs.py --sync",
        },
        **payload,
    }


def make_json_operation(target: str, category: str, destination: Path, payload: dict[str, Any]) -> Operation:
    if destination.exists() and not is_managed_json(destination):
        return Operation(target, category, SOURCE_MCP, destination, "json", "conflict", "unmanaged target exists")
    return Operation(
        target,
        category,
        SOURCE_MCP,
        destination,
        "json",
        "planned",
        json_data=build_managed_json(target, payload, SOURCE_MCP),
    )


def copilot_skill_reports() -> list[Operation]:
    ops: list[Operation] = []
    for skill_dir in source_skill_dirs():
        ops.append(
            Operation(
                "copilot",
                "skills",
                skill_dir / "SKILL.md",
                None,
                "report",
                "native",
                "GitHub Copilot can read .agents/skills directly",
            )
        )
    return ops


def target_operations(target: str) -> list[Operation]:
    ops: list[Operation] = []
    if target == "copilot":
        for source in source_agents():
            ops.append(make_markdown_copy_operation(target, "agents", source, ROOT / ".github" / "agents" / source.name))
        ops.extend(copilot_skill_reports())
        ops.append(make_json_operation(target, "mcp", ROOT / ".vscode" / "mcp.json", mcp_source_json()))
    elif target == "codex":
        ops.extend(
            [
                Operation(target, "agents", None, None, "report", "degraded", "Rely on root AGENTS.md and canonical .agents"),
                Operation(target, "skills", None, None, "report", "native", "Codex discovers skills from canonical .agents/skills"),
                Operation(target, "mcp", None, None, "report", "degraded", "No repo-local Codex MCP mirror generated by default"),
            ]
        )
    else:
        fail(f"unsupported target: {target}")
    return ops


def planned_operations(targets: list[str]) -> list[Operation]:
    ops: list[Operation] = []
    for target in targets:
        ops.extend(target_operations(target))
    return ops


def write_operation(op: Operation) -> None:
    if op.destination is None:
        return
    op.destination.parent.mkdir(parents=True, exist_ok=True)
    if op.kind == "markdown":
        op.destination.write_text(op.content or "", encoding="utf-8")
    elif op.kind == "json":
        op.destination.write_text(json.dumps(op.json_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        fail(f"cannot write unsupported operation kind: {op.kind}")


def validate_operation(op: Operation) -> str | None:
    if op.destination is None or op.status not in {"planned", "native", "degraded"}:
        return None
    if op.kind == "report":
        return None
    if not op.destination.exists():
        return f"missing generated file: {relative_to_root(op.destination)}"
    if op.kind == "markdown":
        actual = op.destination.read_text(encoding="utf-8")
        if actual != (op.content or ""):
            return f"drift detected: {relative_to_root(op.destination)}"
    elif op.kind == "json":
        actual = json.loads(op.destination.read_text(encoding="utf-8"))
        if actual != op.json_data:
            return f"drift detected: {relative_to_root(op.destination)}"
    return None


def summarize(ops: list[Operation]) -> str:
    lines = ["Compatibility summary:"]
    for target in TARGETS:
        target_ops = [op for op in ops if op.target == target]
        if not target_ops:
            continue
        by_category: dict[str, str] = {}
        for category in ("agents", "skills", "mcp"):
            cat_ops = [op for op in target_ops if op.category == category]
            if not cat_ops:
                by_category[category] = "n/a"
                continue
            statuses = {op.status for op in cat_ops}
            if "conflict" in statuses:
                by_category[category] = "conflict"
            elif "degraded" in statuses:
                by_category[category] = "degraded"
            elif "native" in statuses and statuses == {"native"}:
                by_category[category] = "native"
            else:
                by_category[category] = "generated"
        lines.append(
            f"- {target}: agents={by_category['agents']}, skills={by_category['skills']}, mcp={by_category['mcp']}"
        )
    return "\n".join(lines)


def print_operations(ops: list[Operation]) -> None:
    print(summarize(ops))
    print("\nOperations:")
    for op in ops:
        left = relative_to_root(op.source) if op.source else "-"
        right = relative_to_root(op.destination) if op.destination else "-"
        print(f"- [{op.target}/{op.category}] {op.status}: {left} -> {right}")
        if op.note:
            print(f"  note: {op.note}")


def parse_args() -> tuple[str, list[str]]:
    parser = argparse.ArgumentParser(description="Sync canonical .agents assets for GitHub Copilot and Codex.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--sync", action="store_true")
    group.add_argument("--validate", action="store_true")
    parser.add_argument("--targets", help="comma-separated subset of copilot,codex (default: both)")
    args = parser.parse_args()

    if args.targets:
        targets = [item.strip() for item in args.targets.split(",") if item.strip()]
    else:
        targets = list(TARGETS)
    invalid = sorted(set(targets) - set(TARGETS))
    if invalid:
        fail(f"invalid targets: {', '.join(invalid)}")

    mode = "check" if args.check else "sync" if args.sync else "validate"
    return mode, targets


def main() -> int:
    ensure_source_tree()
    mode, targets = parse_args()
    ops = planned_operations(targets)

    if mode == "check":
        print_operations(ops)
        return 0

    if mode == "sync":
        print_operations(ops)
        for op in ops:
            if op.status == "planned":
                write_operation(op)
        conflicts = [op for op in ops if op.status == "conflict"]
        if conflicts:
            print("\nSync completed with unmanaged conflicts left in place.")
            return 1
        print("\nSync complete.")
        return 0

    if mode == "validate":
        print_operations(ops)
        errors = [err for op in ops if (err := validate_operation(op))]
        if errors:
            print("\nValidation failed:", file=sys.stderr)
            for err in errors:
                print(f"- {err}", file=sys.stderr)
            return 1
        print("\nValidation passed.")
        return 0

    fail(f"unknown mode: {mode}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
