"""Contract tests for the curated Claude Code package.

``plugins/agi-super-team-claudecode`` ships the Claude Code-specific layer for
users who install through Claude Code's own marketplace instead of the generic
installer. Everything shared -- that the package is current, that it matches the
adapter byte-for-byte, that it carries no canonical Skill bodies -- lives in
``PackageConformanceTests``. This file adds only what is specific to Claude Code.
"""

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness_package_fixture import (  # noqa: E402
    BY_HARNESS,
    PackageConformanceTests,
    ROOT,
)


SPEC = BY_HARNESS["claude-code"]
PLUGIN_ROOT = SPEC.plugin_root
AGENTS_ROOT = PLUGIN_ROOT / ".claude" / "agents"

# Every canonical role, and the managers allowed to delegate. Kept here rather
# than derived from the adapter so the test fails if the adapter's manager set
# ever changes silently.
MANAGERS = {
    "cto", "cpo", "cco", "cfo", "cdo", "cqo", "cmo", "cro", "cso", "coo", "clo",
}


class ClaudeCodePackageTests(PackageConformanceTests, unittest.TestCase):
    SPEC = SPEC

    def test_every_canonical_role_has_an_agent_definition(self) -> None:
        manifest = json.loads(
            (ROOT / "config/team-manifest.json").read_text(encoding="utf-8")
        )
        expected = {f"ast-{agent['id']}.md" for agent in manifest["agents"]}
        actual = {path.name for path in AGENTS_ROOT.glob("ast-*.md")}
        self.assertEqual(actual, expected)

    def test_frontmatter_matches_the_declared_role(self) -> None:
        """A manager may delegate; a leaf may not. Claude Code encodes that in
        `disallowedTools`, so the frontmatter is the capability boundary."""

        for path in sorted(AGENTS_ROOT.glob("ast-*.md")):
            role_id = path.name[len("ast-") : -len(".md")]
            with self.subTest(role=role_id):
                text = path.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("---\n"), "frontmatter must come first")
                frontmatter = text.split("---", 2)[1]
                self.assertIn(f'name: ast-{role_id}', frontmatter)
                self.assertIn("model: inherit", frontmatter)
                if role_id in MANAGERS or role_id == "ceo":
                    self.assertNotIn(
                        "disallowedTools",
                        frontmatter,
                        "a delegating role must be able to call the Agent tool",
                    )
                    self.assertIn("Agent 工具", text)
                else:
                    self.assertIn(
                        "disallowedTools: Agent",
                        frontmatter,
                        "a leaf must not be able to continue delegating",
                    )
                    self.assertIn("不得创建或调用其他 Agent", text)

    def test_skills_frontmatter_lists_only_real_canonical_skills(self) -> None:
        """`skills:` is Claude Code's preload field, so a name that is not a real
        Skill silently preloads nothing."""

        available = {
            path.name
            for path in (ROOT / "skills").iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        }
        found = False
        for path in sorted(AGENTS_ROOT.glob("ast-*.md")):
            frontmatter = path.read_text(encoding="utf-8").split("---", 2)[1]
            if "skills:" not in frontmatter:
                continue
            found = True
            for line in frontmatter.splitlines():
                line = line.strip()
                if not line.startswith("- "):
                    continue
                name = line[2:].strip()
                with self.subTest(agent=path.name, skill=name):
                    self.assertRegex(name, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
                    self.assertIn(name, available)
        self.assertTrue(found, "at least one role assigns canonical Skills")

    def test_orchestrator_skill_is_the_entry_point(self) -> None:
        skill = (
            PLUGIN_ROOT
            / ".claude"
            / "skills"
            / "agi-super-team-orchestrator"
            / "SKILL.md"
        )
        text = skill.read_text(encoding="utf-8")
        self.assertIn("name: agi-super-team-orchestrator", text)
        self.assertIn("Agent` 工具调用 `ast-ceo`", text)
        self.assertIn("ast-governor", text)
        # The adapter must not claim a nested dispatch happened when the client
        # could not perform one.
        self.assertIn("不得伪称发生了嵌套委派", text)
        # And it must not claim runtime verification this package cannot have.
        self.assertIn("待验证", text)

    def test_connection_spec_maps_every_role_and_its_delegates(self) -> None:
        spec = json.loads(
            (PLUGIN_ROOT / ".claude" / "agi-super-team" / "connection.json").read_text(
                encoding="utf-8"
            )
        )
        manifest = json.loads(
            (ROOT / "config/team-manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            spec["agentMap"],
            {agent["id"]: f"ast-{agent['id']}" for agent in manifest["agents"]},
        )
        self.assertEqual(
            set(spec["managerAgentMap"]),
            MANAGERS,
            "the delegating managers are the eight C-suite owners plus the eleven executives",
        )
        self.assertEqual(spec["destinations"]["agentRoot"], "./.claude/agents")
        self.assertEqual(
            spec["cleanClientReceipt"]["configEnvironmentVariable"],
            "CLAUDE_CONFIG_DIR",
        )
        self.assertEqual(spec["expectedArtifacts"]["canonicalAgents"], 14)
        self.assertEqual(
            spec["expectedArtifacts"]["specialistAgents"],
            0,
            "this package ships no specialist pyramid; that is the installer's --all-subagents route",
        )

    def test_marketplace_entry_points_at_this_package(self) -> None:
        """Without the marketplace entry the package is on disk but uninstallable."""

        marketplace = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        by_name = {entry["name"]: entry for entry in marketplace["plugins"]}
        self.assertIn(SPEC.package, by_name)
        self.assertEqual(by_name[SPEC.package]["source"], f"./plugins/{SPEC.package}")

    def test_manifest_carries_no_component_paths(self) -> None:
        """The plugin manifest is metadata only; components are found by layout.

        Claude Code locates `agents/` and `skills/` relative to the plugin root
        without being told. Its manifest schema also rejects unknown fields, so
        adding an `agents` key is not a harmless declaration -- `claude plugin
        validate` reports it as `Invalid input` and the whole plugin fails
        validation. The package layout is asserted separately, right here, so
        dropping the key cannot silently drop the components too.
        """

        document = json.loads(SPEC.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(document["name"], SPEC.package)
        self.assertIn("Evidence-backed", document["description"])
        for forbidden in ("agents", "skills", "skillsDir", "commands", "hooks"):
            with self.subTest(field=forbidden):
                self.assertNotIn(
                    forbidden,
                    document,
                    f"{forbidden} is not a valid Claude Code plugin.json field",
                )

        # Components live where Claude Code looks for them, not where a
        # manifest points.
        self.assertEqual(
            len(list(AGENTS_ROOT.glob("ast-*.md"))), 14, "agents/ must ship the roles"
        )


    @unittest.skipUnless(
        shutil.which("claude"),
        "the Claude Code CLI is not installed; the field assertions above still run",
    )
    def test_marketplace_manifest_passes_the_client_validator(self) -> None:
        """Run the real validator when the client is available.

        The field assertions above encode what the validator rejects; this runs
        it, so the package is checked against the client rather than against my
        reading of it. `claude plugin validate` rejects unknown fields (it is
        how the `agents` key was caught), so a passing run is a genuine
        structural receipt for the marketplace manifest and every package it
        lists. Runtime evidence stays `pending` -- this proves the manifest
        parses, not that the client loads the agents.
        """

        completed = subprocess.run(
            ["claude", "plugin", "validate", "."],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        output = completed.stdout + completed.stderr
        self.assertNotIn("Found 1 error", output)
        self.assertIn("Validation passed", output)


if __name__ == "__main__":
    unittest.main()
