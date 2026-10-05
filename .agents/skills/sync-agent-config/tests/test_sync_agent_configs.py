from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sync_agent_configs.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sync_agent_configs", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SyncAgentConfigsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".agents" / "skills" / "demo-skill").mkdir(parents=True)
        (self.root / ".agents" / "skills" / "demo-skill" / "SKILL.md").write_text(
            "---\nname: demo-skill\ndescription: Demo skill\n---\n\n# Demo\n",
            encoding="utf-8",
        )
        (self.root / ".agents" / "plan.agent.md").write_text("---\nname: plan\n---\n", encoding="utf-8")
        (self.root / ".agents" / "mcp.json").write_text(
            json.dumps({"servers": {"docs": {"type": "http", "url": "https://example.test/mcp"}}}),
            encoding="utf-8",
        )
        self.module = load_module()
        self.old_cwd = Path.cwd()
        os.chdir(self.root)
        self.module.ROOT = self.root
        self.module.SOURCE_ROOT = self.root / ".agents"
        self.module.SOURCE_SKILLS = self.module.SOURCE_ROOT / "skills"
        self.module.SOURCE_MCP = self.module.SOURCE_ROOT / "mcp.json"

    def tearDown(self) -> None:
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def test_supported_targets_are_copilot_and_codex(self) -> None:
        self.assertEqual(self.module.TARGETS, ("copilot", "codex"))

    def test_copilot_generates_agents_mcp_and_uses_canonical_skills(self) -> None:
        ops = self.module.target_operations("copilot")
        agent = next(op for op in ops if op.destination == self.root / ".github" / "agents" / "plan.agent.md")
        self.assertEqual(agent.status, "planned")
        self.assertTrue(agent.content.startswith("<!-- Managed by sync-agent-config;"))
        mcp = next(op for op in ops if op.destination == self.root / ".vscode" / "mcp.json")
        self.assertEqual(mcp.json_data["servers"]["docs"]["url"], "https://example.test/mcp")
        skills = [op for op in ops if op.category == "skills"]
        self.assertTrue(skills)
        self.assertTrue(all(op.status == "native" for op in skills))

    def test_codex_uses_canonical_agents_and_skills(self) -> None:
        ops = self.module.target_operations("codex")
        actual = {op.category: op.status for op in ops}
        expected = {"agents": "degraded", "skills": "native", "mcp": "degraded"}
        self.assertEqual(actual, expected)

    def test_unmanaged_copilot_agent_conflict_is_reported(self) -> None:
        target = self.root / ".github" / "agents" / "plan.agent.md"
        target.parent.mkdir(parents=True)
        target.write_text("manual\n", encoding="utf-8")
        ops = self.module.target_operations("copilot")
        op = next(op for op in ops if op.destination == target)
        self.assertEqual(op.status, "conflict")

    def test_validate_detects_drift(self) -> None:
        ops = self.module.target_operations("copilot")
        planned = [op for op in ops if op.status == "planned"]
        for op in planned:
            self.module.write_operation(op)
        agent_target = self.root / ".github" / "agents" / "plan.agent.md"
        agent_target.write_text("tampered\n", encoding="utf-8")
        drift = [self.module.validate_operation(op) for op in planned]
        self.assertTrue(any(msg and "drift detected" in msg for msg in drift))


if __name__ == "__main__":
    unittest.main()
