#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
SOURCE_ROOT = ROOT / ".agents"
SOURCE_SKILLS = SOURCE_ROOT / "skills"
SOURCE_MCP = SOURCE_ROOT / "mcp.json"
SOURCE_AGENTS_GLOB = "*.agent.md"

TARGETS = ("claude", "cursor", "copilot", "opencode", "codex", "droid")
MODES = ("--check", "--sync", "--validate")

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


def relative_to_source(path: Path) -> str:
    return path.relative_to(SOURCE_ROOT).as_posix()


def build_header(target: str, source: Path) -> str:
    return HEADER_TEMPLATE.format(target=target, source=relative_to_root(source))


def comment_prefix_for(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix in {".md", ".mdc"}:
        return "<!-- {text} -->\n"
    if suffix in {".py", ".sh", ".txt", ".yml", ".yaml", ".toml"}:
        return "# {text}\n"
    return None


def build_text_header(target: str, source: Path, destination: Path) -> str:
    template = comment_prefix_for(destination)
    if template is None:
        return ""
    text = (
        f"{MANAGED_MARKER}; target={target}; source={relative_to_root(source)}; "
        "regenerate=python3 .agents/skills/sync-agent-config/scripts/sync_agent_configs.py --sync"
    )
    return template.format(text=text)


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


def make_text_copy_operation(target: str, category: str, source: Path, destination: Path) -> Operation:
    body = source.read_text(encoding="utf-8")
    header = build_text_header(target, source, destination)
    content = header + body if header else body
    if destination.exists() and not is_managed_markdown(destination) and header:
        return Operation(target, category, source, destination, "text-copy", "conflict", "unmanaged target exists")
    if destination.exists() and not header:
        return Operation(
            target,
            category,
            source,
            destination,
            "binary-or-text-copy",
            "conflict",
            "cannot safely manage existing unsupported file type",
        )
    kind = "text-copy" if header else "binary-or-text-copy"
    return Operation(target, category, source, destination, kind, "planned", content=content)


def copy_skill_tree_operations(target: str, destination_root: Path) -> list[Operation]:
    ops: list[Operation] = []
    for skill_dir in source_skill_dirs():
        for source in sorted(skill_dir.rglob("*")):
            if source.is_dir():
                continue
            destination = destination_root / source.relative_to(SOURCE_SKILLS)
            if source.name == "SKILL.md":
                ops.append(make_markdown_copy_operation(target, "skills", source, destination))
            else:
                ops.append(make_text_copy_operation(target, "skills", source, destination))
    return ops


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


def make_jsonc_operation(
    target: str, category: str, destination: Path, payload: dict[str, Any], source: Path, prelude_comment: str
) -> Operation:
    if destination.exists() and not is_managed_json(destination):
        return Operation(target, category, source, destination, "jsonc", "conflict", "unmanaged target exists")
    data = build_managed_json(target, payload, source)
    content = (
        f"// {prelude_comment}\n"
        f"// regenerate: python3 .agents/skills/sync-agent-config/scripts/sync_agent_configs.py --sync\n"
        + json.dumps(data, indent=2, sort_keys=True)
        + "\n"
    )
    return Operation(target, category, source, destination, "jsonc", "planned", content=content)


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


def opencode_skill_reports() -> list[Operation]:
    ops: list[Operation] = []
    for skill_dir in source_skill_dirs():
        ops.append(
            Operation(
                "opencode",
                "skills",
                skill_dir / "SKILL.md",
                None,
                "report",
                "native",
                "OpenCode can read .agents/skills directly",
            )
        )
    return ops


def cursor_rule_operation() -> Operation:
    destination = ROOT / ".cursor" / "rules" / "agents-and-skills-index.mdc"
    header = build_header("cursor", SOURCE_ROOT / "skills").strip()
    body_lines = [
        "---",
        "description: Generated index of canonical .agents agents and skills",
        "alwaysApply: true",
        "---",
        "",
        header,
        "",
        "# Canonical Agent Assets",
        "",
        "This file is generated from `.agents`.",
        "Use the canonical files there when you need the full definitions.",
        "",
        "## Custom Agents",
        "",
    ]
    for agent_file in source_agents():
        body_lines.append(f"- `{agent_file.stem}`: `{relative_to_root(agent_file)}`")
    body_lines.extend(["", "## Skills", ""])
    for skill_dir in source_skill_dirs():
        skill_md = skill_dir / "SKILL.md"
        description = extract_description(skill_md)
        body_lines.append(f"- `{skill_dir.name}`: {description} (`{relative_to_root(skill_md)}`)")
    source = SOURCE_ROOT / "skills"
    content = "\n".join(body_lines) + "\n"
    if destination.exists() and not is_managed_markdown(destination):
        return Operation("cursor", "skills", source, destination, "markdown", "conflict", "unmanaged target exists")
    return Operation("cursor", "skills", source, destination, "markdown", "planned", content=content)


def extract_description(skill_md: Path) -> str:
    lines = skill_md.read_text(encoding="utf-8").splitlines()
    in_frontmatter = False
    for line in lines:
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter and line.startswith("description:"):
            return line.split(":", 1)[1].strip()
    return "No description found"


def target_operations(target: str) -> list[Operation]:
    ops: list[Operation] = []
    if target == "claude":
        for source in source_agents():
            dest_name = source.name.replace(".agent.md", ".md")
            ops.append(make_markdown_copy_operation(target, "agents", source, ROOT / ".claude" / "agents" / dest_name))
        ops.extend(copy_skill_tree_operations(target, ROOT / ".claude" / "skills"))
        ops.append(make_json_operation(target, "mcp", ROOT / ".mcp.json", mcp_source_json()))
    elif target == "cursor":
        ops.append(
            Operation(
                target,
                "agents",
                None,
                None,
                "report",
                "unsupported",
                "Cursor has no direct custom-agent mirror for .agents",
            )
        )
        ops.append(cursor_rule_operation())
        ops.append(
            make_json_operation(
                target,
                "mcp",
                ROOT / ".cursor" / "mcp.json",
                {"mcpServers": mcp_source_json().get("servers", {})},
            )
        )
    elif target == "copilot":
        for source in source_agents():
            ops.append(make_markdown_copy_operation(target, "agents", source, ROOT / ".github" / "agents" / source.name))
        ops.extend(copilot_skill_reports())
        ops.append(make_json_operation(target, "mcp", ROOT / ".vscode" / "mcp.json", mcp_source_json()))
    elif target == "opencode":
        for source in source_agents():
            dest_name = source.name.replace(".agent.md", ".md")
            ops.append(make_markdown_copy_operation(target, "agents", source, ROOT / ".opencode" / "agents" / dest_name))
        ops.extend(opencode_skill_reports())
        payload = {
            "$schema": "https://opencode.ai/config.json",
            "instructions": ["AGENTS.md"],
            "mcp": mcp_source_json().get("servers", {}),
        }
        ops.append(
            make_jsonc_operation(
                target,
                "mcp",
                ROOT / "opencode.jsonc",
                payload,
                SOURCE_MCP,
                "Managed by sync-agent-config for OpenCode",
            )
        )
    elif target == "codex":
        ops.extend(
            [
                Operation(target, "agents", None, None, "report", "degraded", "Rely on root AGENTS.md and canonical .agents"),
                Operation(target, "skills", None, None, "report", "degraded", "Rely on canonical .agents without a repo-local mirror"),
                Operation(target, "mcp", None, None, "report", "degraded", "No repo-local Codex MCP mirror generated by default"),
            ]
        )
    elif target == "droid":
        for source in source_agents():
            dest_name = source.name.replace(".agent.md", ".md")
            ops.append(make_markdown_copy_operation(target, "agents", source, ROOT / ".factory" / "droids" / dest_name))
        ops.extend(copy_skill_tree_operations(target, ROOT / ".factory" / "skills"))
        ops.append(
            make_json_operation(
                target,
                "mcp",
                ROOT / ".factory" / "mcp.json",
                {"mcpServers": mcp_source_json().get("servers", {})},
            )
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
    elif op.kind == "text-copy":
        op.destination.write_text(op.content or "", encoding="utf-8")
    elif op.kind == "binary-or-text-copy":
        shutil.copyfile(op.source, op.destination)
    elif op.kind == "json":
        op.destination.write_text(json.dumps(op.json_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elif op.kind == "jsonc":
        op.destination.write_text(op.content or "", encoding="utf-8")
    else:
        fail(f"cannot write unsupported operation kind: {op.kind}")


def validate_operation(op: Operation) -> str | None:
    if op.destination is None or op.status not in {"planned", "native", "degraded", "unsupported"}:
        return None
    if op.kind == "report":
        return None
    if not op.destination.exists():
        return f"missing generated file: {relative_to_root(op.destination)}"
    if op.kind == "markdown":
        actual = op.destination.read_text(encoding="utf-8")
        if actual != (op.content or ""):
            return f"drift detected: {relative_to_root(op.destination)}"
    elif op.kind == "text-copy":
        actual = op.destination.read_text(encoding="utf-8")
        if actual != (op.content or ""):
            return f"drift detected: {relative_to_root(op.destination)}"
    elif op.kind == "binary-or-text-copy":
        if op.destination.read_bytes() != op.source.read_bytes():
            return f"drift detected: {relative_to_root(op.destination)}"
    elif op.kind == "json":
        actual = json.loads(op.destination.read_text(encoding="utf-8"))
        if actual != op.json_data:
            return f"drift detected: {relative_to_root(op.destination)}"
    elif op.kind == "jsonc":
        actual = op.destination.read_text(encoding="utf-8")
        if actual != (op.content or ""):
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
            elif "unsupported" in statuses:
                by_category[category] = "unsupported"
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
    parser = argparse.ArgumentParser(description="Sync canonical .agents assets into tool-specific folders.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--sync", action="store_true")
    group.add_argument("--validate", action="store_true")
    parser.add_argument("--targets", help="comma-separated subset of targets")
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
