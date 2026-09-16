"""Contract tests for the curated OpenClaw package.

``plugins/agi-super-team-openclaw`` ships the OpenClaw-specific layer for users
who install through ``openclaw plugins install`` instead of the generic
installer. Everything shared lives in ``PackageConformanceTests``; this file
adds only what is specific to OpenClaw.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness_package_fixture import (  # noqa: E402
    BY_HARNESS,
    PackageConformanceTests,
    ROOT,
)


SPEC = BY_HARNESS["openclaw"]
PLUGIN_ROOT = SPEC.plugin_root
WORKSPACE_ROOT = PLUGIN_ROOT / "agency-agents" / "agi-super-team"
ORCHESTRATOR = (
    PLUGIN_ROOT
    / "skills"
    / "agi-super-team"
    / "agi-super-team-orchestrator"
    / "SKILL.md"
)

# The files OpenClaw reads as a role's workspace bootstrap. A role ships only
# the ones that exist in the canonical agent directory, so this is the full set
# rather than a required set.
ROLE_FILES = ("IDENTITY.md", "SOUL.md", "AGENTS.md", "USER.md", "TOOLS.md", "MEMORY.md")


class OpenClawPackageTests(PackageConformanceTests, unittest.TestCase):
    SPEC = SPEC

    def test_every_canonical_role_has_a_workspace(self) -> None:
        manifest = json.loads(
            (ROOT / "config/team-manifest.json").read_text(encoding="utf-8")
        )
        expected = {f"ast-{agent['id']}" for agent in manifest["agents"]}
        actual = {path.name for path in WORKSPACE_ROOT.iterdir() if path.is_dir()}
        self.assertEqual(actual, expected)
        self.assertEqual(len(expected), 14)

    def test_role_workspaces_mirror_the_canonical_files(self) -> None:
        """The adapter copies the role files that exist; it does not invent any.

        A role that gained a file upstream would be silently missing it here,
        so the package is compared against the canonical agent directory rather
        than against a hard-coded list.
        """

        manifest = json.loads(
            (ROOT / "config/team-manifest.json").read_text(encoding="utf-8")
        )
        for agent in manifest["agents"]:
            canonical = ROOT / "agents" / agent["id"]
            expected = {name for name in ROLE_FILES if (canonical / name).is_file()}
            workspace = WORKSPACE_ROOT / f"ast-{agent['id']}"
            actual = {path.name for path in workspace.iterdir() if path.is_file()}
            with self.subTest(role=agent["id"]):
                self.assertEqual(actual, expected)

    def test_no_workspace_carries_a_routing_block_at_default_selection(self) -> None:
        """This package installs no specialist pyramid, so no manager has
        delegates and no workspace receives a routing block.

        The block is appended only to a manager that has at least one spawnable
        target. With `groups` empty -- which is what the package selects -- the
        adapter produces none, and the orchestrator Skill's manager-boundary
        section is consequently empty. Both are asserted, because a package
        that suddenly grew a routing block would be claiming delegated roles it
        does not ship.
        """

        begin = "<!-- AGI-SUPER-TEAM:OPENCLAW-ROUTING:BEGIN -->"
        end = "<!-- AGI-SUPER-TEAM:OPENCLAW-ROUTING:END -->"
        for path in sorted(WORKSPACE_ROOT.glob("ast-*/AGENTS.md")):
            with self.subTest(role=path.parent.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn(begin, text)
                self.assertNotIn(end, text)
                self.assertNotIn("sessions_spawn(", text)

    def test_orchestrator_skill_uses_the_native_session_tools(self) -> None:
        text = ORCHESTRATOR.read_text(encoding="utf-8")
        self.assertIn("name: agi-super-team-orchestrator", text)
        # These are the OpenClaw tools the routing depends on; naming them is
        # the difference between a usable entry point and generic advice.
        for tool in (
            "agents_list",
            "sessions_spawn",
            "sessions_yield",
            "sessions_history",
        ):
            with self.subTest(tool=tool):
                self.assertIn(tool, text)
        self.assertIn("ast-governor", text)
        # The Governor has to check the raw child session, not a CEO summary.
        self.assertIn("不能只接受 CEO 转述", text)
        self.assertIn("禁止生成 channel bindings", text)
        # The canonical entry Skill is reached by relative path.
        self.assertIn("../orchestrate-agi-super-team/SKILL.md", text)

    def test_connection_spec_registers_agents_merge_safely(self) -> None:
        """The manifest installs files; this spec is what registers agents.

        The merge contract is the part a user cannot easily audit, so its
        safety properties are asserted rather than assumed.
        """

        spec = json.loads(
            (PLUGIN_ROOT / "agi-super-team" / "connection.json").read_text(
                encoding="utf-8"
            )
        )
        contract = spec["mergeContract"]
        self.assertEqual(contract["path"], "agents.list")
        self.assertEqual(contract["key"], "id")
        self.assertEqual(contract["strategy"], "upsert-managed-preserve-unmanaged")
        self.assertEqual(contract["managedPrefix"], "ast-")
        self.assertTrue(contract["preserveUnmanaged"])
        self.assertFalse(
            contract["removeUnmentionedManaged"],
            "a later install must never delete an agent a previous one added",
        )
        self.assertEqual(contract["conflictPolicy"], "fail-unless-previewed")
        self.assertEqual(contract["mapStrategy"], "deep-merge")
        self.assertEqual(spec["requirements"]["requiredMaxDepth"], 2)
        self.assertEqual(spec["requirements"]["maxChildrenPerAgent"], 2)

    def test_connection_spec_agent_list_matches_the_shipped_workspaces(self) -> None:
        spec = json.loads(
            (PLUGIN_ROOT / "agi-super-team" / "connection.json").read_text(
                encoding="utf-8"
            )
        )
        entries = spec["configPatch"]["agents"]["list"]
        manifest = json.loads(
            (ROOT / "config/team-manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            [entry["id"] for entry in entries],
            [f"ast-{agent['id']}" for agent in manifest["agents"]],
        )
        for entry in entries:
            with self.subTest(role=entry["id"]):
                # This is the one place a package cannot avoid an absolute path:
                # OpenClaw resolves workspaces, not package-relative names. It
                # is still asserted to be package-relative in shape rather than
                # pointing at the machine that generated it.
                self.assertEqual(Path(entry["workspace"]).name, entry["id"])
                self.assertNotIn("\\", entry["workspace"])

    def test_delegation_boundaries_follow_the_selected_roles(self) -> None:
        """Who may spawn whom, given that this package selects no specialists.

        The coordinator reaches every other canonical role. Everything else --
        every C-suite manager included -- is treated as a leaf, because a
        manager's allowlist is built from the specialist pyramid and this
        package ships none. That is a real limitation of the curated package,
        not an oversight, and installing `--all-subagents` through the generic
        installer is what turns the managers into delegating nodes.
        """

        spec = json.loads(
            (PLUGIN_ROOT / "agi-super-team" / "connection.json").read_text(
                encoding="utf-8"
            )
        )
        entries = {entry["id"]: entry for entry in spec["configPatch"]["agents"]["list"]}
        manifest = json.loads(
            (ROOT / "config/team-manifest.json").read_text(encoding="utf-8")
        )
        canonical = {f"ast-{agent['id']}" for agent in manifest["agents"]}

        ceo = entries["ast-ceo"]
        self.assertEqual(
            set(ceo["subagents"]["allowAgents"]),
            canonical - {"ast-ceo"},
            "the coordinator may call every other canonical role and nothing else",
        )
        self.assertTrue(ceo["subagents"]["requireAgentId"])
        self.assertIn("agi-super-team-orchestrator", ceo["skills"])
        self.assertNotIn("tools", ceo, "the coordinator must be able to spawn")

        for role_id in sorted(canonical - {"ast-ceo"}):
            entry = entries[role_id]
            with self.subTest(role=role_id):
                self.assertEqual(
                    entry["subagents"]["allowAgents"],
                    [],
                    "no role has a shipped delegate while the specialist pyramid is absent",
                )
                self.assertTrue(entry["subagents"]["requireAgentId"])
                self.assertIn("sessions_spawn", entry["tools"]["deny"])

    def test_skill_names_are_canonical_not_packaged(self) -> None:
        """Every assigned Skill an entry names must exist under the canonical root.

        The package ships no Skill bodies, so an entry naming a Skill the
        repository does not have would reference something the installer cannot
        vend and the harness cannot load. ``agi-super-team-orchestrator`` is
        excluded from that rule: it is the adapter's own generated entry point,
        written into the managed Skill root by the installer rather than read
        from the canonical tree.
        """

        spec = json.loads(
            (PLUGIN_ROOT / "agi-super-team" / "connection.json").read_text(
                encoding="utf-8"
            )
        )
        available = {
            path.name
            for path in (ROOT / "skills").iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        }
        generated_entry = "agi-super-team-orchestrator"
        named: set[str] = set()
        for entry in spec["configPatch"]["agents"]["list"]:
            named.update(entry["skills"])
        self.assertIn(generated_entry, named)
        self.assertIn("orchestrate-agi-super-team", available)
        for name in sorted(named - {generated_entry}):
            with self.subTest(skill=name):
                self.assertIn(name, available)

    def test_manifest_is_a_native_openclaw_manifest(self) -> None:
        document = json.loads(SPEC.manifest_path.read_text(encoding="utf-8"))
        # OpenClaw requires an id and an inline JSON schema, even for a plugin
        # that accepts no configuration. A manifest missing either is rejected
        # before the install record is written.
        self.assertEqual(document["id"], SPEC.package)
        self.assertIn("configSchema", document)
        self.assertEqual(document["configSchema"]["type"], "object")
        self.assertIn("Evidence-backed", document["description"])

    def test_package_does_not_also_carry_a_client_specific_marker(self) -> None:
        """OpenClaw auto-detects client bundles, and that detection wins.

        A package carrying `.claude-plugin/` alongside the native manifest would
        be read as a Claude bundle, and the `agents.list` wiring this package
        exists to deliver would never be applied.
        """

        for marker in (".claude-plugin", ".codex-plugin", ".cursor-plugin"):
            with self.subTest(marker=marker):
                self.assertFalse(
                    (PLUGIN_ROOT / marker).exists(),
                    "a client-specific marker would shadow the native manifest",
                )


if __name__ == "__main__":
    unittest.main()
