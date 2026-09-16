"""Contract tests for the curated DSH package.

``plugins/agi-super-team-dsh`` ships the DSH-specific layer for users who
install through ``dsh plugin add`` instead of the generic installer. Everything
shared lives in ``PackageConformanceTests``; this file adds only what is
specific to DSH.

DSH is the harness where "an agent is one file" is least true, so most of these
tests are about the three mechanisms actually being present and coherent with
one another rather than about any single artifact.
"""

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness_package_fixture import (  # noqa: E402
    BY_HARNESS,
    PackageConformanceTests,
    ROOT,
)


SPEC = BY_HARNESS["dsh"]
PLUGIN_ROOT = SPEC.plugin_root
PRESET_ROOT = PLUGIN_ROOT / ".agent-presets" / "ast-team"
ORCHESTRATOR = (
    PLUGIN_ROOT
    / "skills"
    / "agi-super-team"
    / "agi-super-team-orchestrator"
    / "SKILL.md"
)


class DshPackageTests(PackageConformanceTests, unittest.TestCase):
    SPEC = SPEC

    def test_all_three_composition_mechanisms_are_present(self) -> None:
        """DSH needs the instruction chain, the patch layer, and the preset.

        None alone carries a role: the global file is advisory, the patch only
        makes Skills reachable, and the preset is where routing actually lives.
        """

        expected = [
            PLUGIN_ROOT / "AGENTS.md",
            PLUGIN_ROOT / "profiles" / "web" / "cordis.patch.yml",
            PRESET_ROOT / "agent.cordis.yml",
            PRESET_ROOT / "preset.yml",
            ORCHESTRATOR,
        ]
        for path in expected:
            with self.subTest(path=path.relative_to(PLUGIN_ROOT).as_posix()):
                self.assertTrue(path.is_file())

    def test_global_instruction_chain_keeps_its_managed_markers(self) -> None:
        """The installer only ever replaces the marked block.

        A file without the markers would be overwritten whole, destroying
        whatever else the user keeps in their global `AGENTS.md`.
        """

        text = (PLUGIN_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertEqual(text.count("<!-- AGI-SUPER-TEAM:CEO:BEGIN -->"), 1)
        self.assertEqual(text.count("<!-- AGI-SUPER-TEAM:CEO:END -->"), 1)
        self.assertLess(
            text.index("<!-- AGI-SUPER-TEAM:CEO:BEGIN -->"),
            text.index("<!-- AGI-SUPER-TEAM:CEO:END -->"),
        )

    def test_patch_reenables_skill_discovery_and_points_at_shared_skills(self) -> None:
        """`dsh-web-app` disables the host skill-filesystem row.

        Re-enabling it is the only way Skills on disk become reachable, so the
        entry is asserted field by field rather than by presence.
        """

        text = (PLUGIN_ROOT / "profiles" / "web" / "cordis.patch.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(text.count("# AGI-SUPER-TEAM:DSH-PATCH:BEGIN"), 1)
        self.assertEqual(text.count("# AGI-SUPER-TEAM:DSH-PATCH:END"), 1)
        self.assertRegex(text, r"(?m)^- id: skill-filesystem$")
        self.assertRegex(text, r'(?m)^  name: "@deepseek-ai/dsh-skill-filesystem"$')
        self.assertRegex(text, r"(?m)^  disabled: false$")
        self.assertRegex(text, r"(?m)^    customSkillDirs:$")
        # The patch and the orchestrator Skill have to agree on one spelling of
        # the shared Skills directory, or the preset points at a directory the
        # patch never registered.
        self.assertIn('      - "./skills/agi-super-team"', text)

    def test_every_canonical_role_has_a_preset_agent_file(self) -> None:
        manifest = json.loads(
            (ROOT / "config/team-manifest.json").read_text(encoding="utf-8")
        )
        expected = {agent["id"] for agent in manifest["agents"]}
        actual = {path.name for path in (PRESET_ROOT / "agents").iterdir() if path.is_dir()}
        self.assertEqual(actual, expected)
        for role_id in sorted(expected):
            with self.subTest(role=role_id):
                role_file = PRESET_ROOT / "agents" / role_id / "AGENTS.md"
                self.assertTrue(role_file.is_file())
                self.assertTrue(role_file.read_text(encoding="utf-8").strip())

    def test_preset_composition_routes_every_role_and_disables_delegation_for_leaves(
        self,
    ) -> None:
        """DSH enforces no per-role boundary, so the composition is the contract.

        The hierarchy therefore has to be readable out of the composed persona:
        the coordinator routes, managers may run short anonymous subtasks, and
        the leaf/Governor rows must forbid it.
        """

        text = (PRESET_ROOT / "agent.cordis.yml").read_text(encoding="utf-8")
        manifest = json.loads(
            (ROOT / "config/team-manifest.json").read_text(encoding="utf-8")
        )
        for agent in manifest["agents"]:
            with self.subTest(role=agent["id"]):
                self.assertIn(f"`ast-{agent['id']}`", text)
        # Manager delegation is bounded by depth and concurrency.
        self.assertIn("总深度不超过二", text)
        self.assertIn("最多两个并发", text)
        # Leaves and the Governor must not spawn further agents.
        self.assertIn("叶子与 Governor 不得继续创建子 Agent", text)
        # High-risk actions stay behind human approval.
        self.assertIn("必须由用户最终批准", text)
        # And nothing may be claimed that was not actually run.
        self.assertIn("不得声称未执行", text)

    def test_orchestrator_skill_names_the_shared_skill_root(self) -> None:
        text = ORCHESTRATOR.read_text(encoding="utf-8")
        self.assertIn("name: agi-super-team-orchestrator", text)
        # The canonical entry Skill is reached by relative path, so the wrapper
        # has to point at it rather than duplicate it.
        self.assertIn("../orchestrate-agi-super-team/SKILL.md", text)
        self.assertIn("DSH 不给每个角色单独的工具边界", text)
        # The canonical checkout location is a build-time placeholder, not one
        # contributor's absolute path.
        self.assertIn("<repository-root>/agents", text)
        self.assertIn("必须由用户最终批准", text)

    def test_connection_spec_documents_the_preset_and_its_limitations(self) -> None:
        spec = json.loads(
            (PLUGIN_ROOT / "agi-super-team" / "connection.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(spec["connectionMode"], "agent-preset-plus-user-patch")
        self.assertEqual(spec["presetId"], "ast-team")
        self.assertEqual(spec["profile"], "web")
        self.assertTrue(spec["activation"]["presetMustBeSelectedByUser"])
        self.assertTrue(spec["activation"]["requiresProfilePatch"])
        self.assertEqual(
            spec["activation"]["entrySkill"], "agi-super-team-orchestrator"
        )
        # The harness limitation is the most important thing a reader can learn
        # here, so it is asserted rather than left to prose.
        limitations = "\n".join(spec["limitations"])
        self.assertIn("no per-role tool or capability boundary", limitations)
        self.assertIn("cannot be merged into", limitations)

    def test_no_specialist_subagents_were_selected(self) -> None:
        spec = json.loads(
            (PLUGIN_ROOT / "agi-super-team" / "connection.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(spec["specialistAgents"], [])
        self.assertFalse(any((PRESET_ROOT / "agents").rglob("subagents")))

    def test_plugin_manifest_declares_the_bundle_layer(self) -> None:
        """The manifest follows the published DSH bundle format.

        A DSH plugin manifest declares exactly one thing that matters here:
        where its patch layer lives. There is no `$schema`, `main`, or `type`
        for a pure bundle package, and asserting their absence keeps someone
        from adding an invented schema URL that points at a missing file.
        """

        document = json.loads(SPEC.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(document["name"], SPEC.package)
        patch = document["dsh"]["bundle"]["patch"]
        self.assertEqual(patch, "./profiles/web/cordis.patch.yml")
        self.assertIn("Evidence-backed", document["description"])
        for unofficial in ("$schema", "main", "type"):
            with self.subTest(key=unofficial):
                self.assertNotIn(unofficial, document)
        # The patch the manifest names has to exist, or the bundle cannot resolve.
        self.assertTrue((PLUGIN_ROOT / patch).is_file())
        # And the manifest's own `files` allowlist must cover everything the
        # package ships, or a published tarball would be missing pieces of the
        # layer it just declared. The manifest itself is excluded: a package
        # manifest is always shipped and never lists itself.
        shipped = {
            path.relative_to(PLUGIN_ROOT).parts[0]
            for path in PLUGIN_ROOT.rglob("*")
            if path.is_file() and path.name != SPEC.manifest
        }
        self.assertTrue(
            shipped <= set(document["files"]),
            f"files allowlist misses: {sorted(shipped - set(document['files']))}",
        )

    def test_version_placeholder_was_substituted(self) -> None:
        document = json.loads(SPEC.manifest_path.read_text(encoding="utf-8"))
        self.assertRegex(document["version"], r"^\d+\.\d+\.\d+$")
        self.assertNotRegex(
            SPEC.manifest_path.read_text(encoding="utf-8"), r"@@VERSION@@"
        )


if __name__ == "__main__":
    unittest.main()
