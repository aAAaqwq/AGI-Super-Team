"""Contract tests for the curated Hermes package.

``plugins/agi-super-team-hermes`` ships the Hermes-specific layer for users who
install through ``hermes plugins install`` instead of the generic installer.
Everything shared lives in ``PackageConformanceTests``; this file adds only what
is specific to Hermes.
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


SPEC = BY_HARNESS["hermes"]
PLUGIN_ROOT = SPEC.plugin_root
ROLE_SKILL_ROOT = PLUGIN_ROOT / "skills" / "agi-super-team-agents"
BLUEPRINT_ROOT = PLUGIN_ROOT / "agi-super-team" / "profiles"

MANAGERS = {
    "cto", "cpo", "cco", "cfo", "cdo", "cqo", "cmo", "cro", "cso", "coo", "clo",
}


class HermesPackageTests(PackageConformanceTests, unittest.TestCase):
    SPEC = SPEC

    def test_every_canonical_role_has_a_skill_and_a_blueprint(self) -> None:
        manifest = json.loads(
            (ROOT / "config/team-manifest.json").read_text(encoding="utf-8")
        )
        role_ids = {agent["id"] for agent in manifest["agents"]}
        self.assertEqual(
            {path.name for path in ROLE_SKILL_ROOT.iterdir() if path.is_dir()},
            {f"ast-{role_id}" for role_id in role_ids},
        )
        self.assertEqual(
            {path.name for path in BLUEPRINT_ROOT.iterdir() if path.is_dir()},
            {f"ast-{role_id}" for role_id in role_ids},
        )

    def test_role_skill_is_a_valid_hermes_skill(self) -> None:
        for path in sorted(ROLE_SKILL_ROOT.glob("ast-*/SKILL.md")):
            with self.subTest(role=path.parent.name):
                text = path.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("---\n"))
                frontmatter, body = text.split("---", 2)[1], text.split("---", 2)[2]
                self.assertIn(f"name: {path.parent.name}", frontmatter)
                self.assertIn("category: agi-super-team-agents", frontmatter)
                self.assertIn("runtimeEvidence: pending", body)

    def test_blueprints_are_inert(self) -> None:
        """A blueprint is not a Profile.

        Creating Profiles, starting a Gateway, or registering Cron is a human
        decision. If a blueprint ever claimed otherwise, the package would
        overstate what installing it does -- so the flags that say "nothing was
        created" are asserted rather than trusted.
        """

        for path in sorted(BLUEPRINT_ROOT.glob("ast-*/profile.json")):
            with self.subTest(profile=path.parent.name):
                blueprint = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(blueprint["harness"], "hermes")
                self.assertEqual(blueprint["profileId"], path.parent.name)
                self.assertTrue(blueprint["blueprintOnly"])
                self.assertFalse(blueprint["runtimeStateCreated"])
                self.assertEqual(blueprint["runtimeEvidence"], "pending")
                self.assertTrue(blueprint["activation"]["humanReviewRequired"])
                self.assertTrue(blueprint["activation"]["profileCreateOrUpdateRequired"])
                self.assertFalse(blueprint["activation"]["performedByAdapter"])
                self.assertEqual(blueprint["schemaVersion"], 1)

    def test_blueprint_role_types_and_delegation_follow_the_hierarchy(self) -> None:
        hierarchy = json.loads(
            (ROOT / "config/agent-hierarchy.json").read_text(encoding="utf-8")
        )
        for path in sorted(BLUEPRINT_ROOT.glob("ast-*/profile.json")):
            role_id = path.parent.name[len("ast-") :]
            blueprint = json.loads(path.read_text(encoding="utf-8"))
            capabilities = blueprint["desiredCapabilities"]
            with self.subTest(role=role_id):
                if role_id == "ceo":
                    self.assertEqual(blueprint["roleType"], "coordinator")
                    self.assertEqual(capabilities["kanbanRole"], "orchestrator")
                elif role_id == "governor":
                    self.assertEqual(blueprint["roleType"], "independent-reviewer")
                    self.assertEqual(capabilities["kanbanRole"], "reviewer")
                elif role_id in MANAGERS:
                    self.assertEqual(blueprint["roleType"], "manager")
                    self.assertEqual(capabilities["kanbanRole"], "worker")
                else:
                    self.assertEqual(blueprint["roleType"], "leaf")
                    self.assertEqual(capabilities["maxConcurrentChildren"], 0)
                    self.assertEqual(capabilities["delegateTask"], "disabled")
                self.assertEqual(
                    capabilities["requiredMaxDepth"], hierarchy["requiredMaxDepth"]
                )

    def test_blueprints_declare_the_shared_skill_root_explicitly(self) -> None:
        """Hermes profiles do not inherit the default profile's Skills.

        Every blueprint therefore has to name the shared Skill directory, or
        the role Skills exist on disk and are invisible at runtime -- and this
        package ships no Skill bodies of its own to fall back on.
        """

        for path in sorted(BLUEPRINT_ROOT.glob("ast-*/profile.json")):
            blueprint = json.loads(path.read_text(encoding="utf-8"))
            visibility = blueprint["profileSkillVisibility"]
            with self.subTest(profile=path.parent.name):
                self.assertEqual(
                    visibility["configurationMode"], "human-review-required"
                )
                self.assertEqual(visibility["configKey"], "skills.external_dirs")
                self.assertFalse(visibility["appliedByAdapter"])
                self.assertTrue(visibility["requiredExternalDirectory"])
                # A Kanban card must pin the role Skill before anything else,
                # or the assignee resolves to nothing. Writing the assignee
                # alone is not enough, so the pin is asserted positionally.
                self.assertEqual(blueprint["kanbanTaskSkills"][0], blueprint["profileId"])
                self.assertEqual(
                    blueprint["kanbanTaskSkills"][1:], blueprint["assignedSkills"]
                )
                self.assertTrue(blueprint["roleSkill"].endswith("/SKILL.md"))

    def test_connection_spec_pins_the_kanban_contract(self) -> None:
        spec = json.loads(
            (PLUGIN_ROOT / "agi-super-team" / "connection.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(spec["connectionMode"], "profiles-kanban-blueprint")
        self.assertEqual(spec["schemaVersion"], 1)
        self.assertFalse(spec["writesRuntimeState"])
        self.assertEqual(spec["sideEffects"], {
            "createProfiles": False,
            "createCron": False,
            "startGateway": False,
        })
        # Hermes's delegate_task has no profile argument; a spec that allowed
        # one would describe a call the harness cannot make.
        self.assertFalse(spec["permissions"]["ceo"]["delegateTask"]["allowed"])
        self.assertFalse(
            spec["permissions"]["ceo"]["delegateTask"]["profileArgumentAllowed"]
        )
        self.assertFalse(spec["permissions"]["leaf"]["delegateTask"]["allowed"])
        self.assertFalse(spec["permissions"]["governor"]["delegateTask"]["allowed"])
        self.assertTrue(spec["permissions"]["governor"]["independent"])
        self.assertTrue(spec["kanbanPolicy"]["roleSkillPinningRequired"])
        self.assertTrue(spec["kanbanPolicy"]["governorRunsInSeparateProfile"])
        self.assertEqual(spec["canary"]["status"], "pending")
        self.assertTrue(spec["canary"]["receiptMustBindRepositoryRevision"])

    def test_manifest_is_a_valid_agent_plugins_v1_manifest(self) -> None:
        """Hermes installs a portable Agent Plugins package.

        The core schema is closed, so this asserts the two things a reader is
        most likely to get wrong: `$schema` is present and canonical, and no
        field outside the permitted set appears -- in particular no `skills`
        key, because Skills are discovered from the fixed `skills/` location
        rather than declared.
        """

        document = json.loads(SPEC.manifest_path.read_text(encoding="utf-8"))
        # Hermes requires the manifest at the package root, not under a
        # harness-named directory the way Codex and Claude Code do.
        self.assertEqual(SPEC.manifest_path.parent, PLUGIN_ROOT)
        self.assertEqual(
            document["$schema"],
            "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        )
        self.assertEqual(document["name"], SPEC.package)
        self.assertIn("Evidence-backed", document["description"])
        # The portable core is a closed top-level object.
        permitted = {
            "$schema",
            "name",
            "version",
            "description",
            "author",
            "homepage",
            "repository",
            "license",
            "keywords",
            "extensions",
        }
        self.assertEqual(
            set(document) - permitted,
            set(),
            "Agent Plugins v1.0.0 permits no other top-level fields",
        )
        self.assertNotIn(
            "skills",
            document,
            "skills are discovered from skills/, not declared in the manifest",
        )
        # Skills still have to be where the format looks for them.
        self.assertTrue((PLUGIN_ROOT / "skills").is_dir())


if __name__ == "__main__":
    unittest.main()
