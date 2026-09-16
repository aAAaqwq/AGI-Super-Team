import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "agi-super-team.mjs"
NODE = os.environ.get("NODE", "node")
ADAPTER_MODULE = ROOT / "bin" / "adapters" / "dsh.mjs"
ADAPTER_MANIFEST = ROOT / "config" / "harness-adapters" / "dsh.json"
ADAPTER_SCHEMA = ROOT / "config" / "harness-adapters" / "dsh.schema.json"

# The placeholder DSH itself writes the first time a profile is booted. A
# patch list is a single YAML document, so this cannot be appended to.
DSH_PLACEHOLDER = (
    "# Your patch layer for this dsh profile, applied after every bundle layer:\n"
    "# a top-level YAML array of loader patch entries (id-targeted config\n"
    "# overrides, disables, and insert lists; `!!js` expressions allowed).\n"
    "[]\n"
)


def run_node(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [NODE, "--input-type=module", "--eval", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


class DshAdapterTests(unittest.TestCase):
    def run_cli(self, home: Path, project: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.pop("DSH_HOME", None)
        environment.pop("DSH_PROFILE", None)
        return subprocess.run(
            [
                NODE,
                str(CLI),
                "--home",
                str(home),
                "--project-dir",
                str(project),
                *arguments,
            ],
            capture_output=True,
            text=True,
            check=False,
            env=environment,
        )

    def test_contract_is_schema_valid_and_maps_all_canonical_roles(self) -> None:
        adapter = json.loads(ADAPTER_MANIFEST.read_text(encoding="utf-8"))
        schema = json.loads(ADAPTER_SCHEMA.read_text(encoding="utf-8"))
        manifest = json.loads(
            (ROOT / "config" / "team-manifest.json").read_text(encoding="utf-8")
        )

        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(adapter)

        self.assertEqual(adapter["harness"], "dsh")
        self.assertEqual(adapter["runtimeEvidence"], "pending")
        self.assertEqual(adapter["requiredMaxDepth"], 2)
        self.assertEqual(adapter["maxConcurrentChildren"], 2)
        self.assertEqual(adapter["coordinator"], "ceo")
        self.assertEqual(adapter["independentReviewer"], "governor")
        self.assertEqual(adapter["defaultProfile"], "web")
        self.assertEqual(adapter["presetId"], "ast-team")
        self.assertEqual(
            set(adapter["presetMap"]),
            {agent["id"] for agent in manifest["agents"]},
        )
        # DSH cannot enforce a per-role boundary; the contract must say so
        # rather than implying parity with the other four harnesses.
        self.assertEqual(
            adapter["delegationPolicy"]["perRoleToolBoundary"],
            "not-enforced-by-harness",
        )
        self.assertEqual(adapter["instructionPolicy"]["authority"], "advisory")

    def test_manifest_entry_satisfies_the_priority_harness_contract(self) -> None:
        adapters = json.loads(
            (ROOT / "config" / "cli-adapters.json").read_text(encoding="utf-8")
        )
        tool = next(item for item in adapters["tools"] if item["id"] == "dsh")

        self.assertEqual(tool["agentMode"], "harness-adapter")
        self.assertEqual(tool["runtimeEvidence"], "pending")
        self.assertEqual(tool["skillSource"], "canonical-assigned")
        self.assertEqual(tool["adapterModule"], "bin/adapters/dsh.mjs")
        self.assertTrue((ROOT / tool["adapterModule"]).is_file())
        self.assertTrue(
            (ROOT / "config" / "harness-adapters" / "dsh.json").is_file()
        )
        self.assertTrue(
            (ROOT / "config" / "harness-adapters" / "dsh.schema.json").is_file()
        )

    def test_install_writes_artifacts_under_agent_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project = root / "project"
            project.mkdir()

            result = self.run_cli(home, project, "--tool", "dsh", "--no-skills", "--install")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            dsh_home = home / ".dsh"
            # `agentPaths` in the CLI manifest must point at a tree that really
            # exists, otherwise the priority-harness guarantee is vacuous.
            self.assertTrue((dsh_home / ".agent-presets/ast-team/agents/ceo/AGENTS.md").is_file())
            self.assertTrue((dsh_home / ".agent-presets/ast-team/agent.cordis.yml").is_file())
            self.assertTrue((dsh_home / ".agent-presets/ast-team/preset.yml").is_file())
            self.assertTrue((dsh_home / "AGENTS.md").is_file())
            self.assertTrue((dsh_home / "agi-super-team/connection.json").is_file())
            self.assertTrue((dsh_home / "profiles/web/cordis.patch.yml").is_file())

            connection = json.loads(
                (dsh_home / "agi-super-team/connection.json").read_text(encoding="utf-8")
            )
            self.assertEqual(connection["harness"], "dsh")
            self.assertEqual(connection["runtimeEvidence"], "pending")
            self.assertEqual(connection["presetId"], "ast-team")
            # The patch must point at the skills root the installer actually
            # wrote to, not a re-derived path.
            patch = (dsh_home / "profiles/web/cordis.patch.yml").read_text(encoding="utf-8")
            self.assertIn(str(dsh_home / "skills/agi-super-team"), patch)
            self.assertNotIn(".dsh/.dsh", patch)

    def test_patch_replaces_the_dsh_placeholder_instead_of_appending(self) -> None:
        """A patch list is one YAML document: appending after `[]` breaks it."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project = root / "project"
            project.mkdir()
            patch_path = home / ".dsh/profiles/web/cordis.patch.yml"
            patch_path.parent.mkdir(parents=True)
            patch_path.write_text(DSH_PLACEHOLDER, encoding="utf-8")

            result = self.run_cli(home, project, "--tool", "dsh", "--no-skills", "--install")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            content = patch_path.read_text(encoding="utf-8")
            self.assertNotIn("[]", content, "placeholder must not survive alongside entries")
            self.assertEqual(content.count("customSkillDirs"), 1)
            self.assertEqual(content.count("- id:"), 1)
            # A second YAML document would start after the placeholder's array.
            self.assertNotIn("\n---", content)

    def test_patch_skips_a_file_that_already_holds_user_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project = root / "project"
            project.mkdir()
            patch_path = home / ".dsh/profiles/web/cordis.patch.yml"
            patch_path.parent.mkdir(parents=True)
            original = (
                "# my own notes\n"
                "- id: my-row\n"
                "  name: '@deepseek-ai/dsh-tool-fs'\n"
                "  disabled: true\n"
            )
            patch_path.write_text(original, encoding="utf-8")

            result = self.run_cli(home, project, "--tool", "dsh", "--no-skills", "--install")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            self.assertEqual(patch_path.read_text(encoding="utf-8"), original)
            # Everything except the patch still installs.
            self.assertTrue(
                (home / ".dsh/.agent-presets/ast-team/agent.cordis.yml").is_file()
            )

    def test_install_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project = root / "project"
            project.mkdir()

            arguments = ("--tool", "dsh", "--no-skills", "--install")
            first = self.run_cli(home, project, *arguments)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            second = self.run_cli(home, project, *arguments)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertIn("add=0 update=0", second.stdout)

    def test_dsh_home_controls_the_installation_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dsh_home = root / "custom-dsh-home"
            project = root / "project"
            project.mkdir()
            environment = os.environ.copy()
            environment.pop("DSH_HOME", None)
            environment["DSH_HOME"] = str(dsh_home)

            result = subprocess.run(
                [
                    NODE,
                    str(CLI),
                    "--project-dir",
                    str(project),
                    "--tool",
                    "dsh",
                    "--no-skills",
                    "--install",
                ],
                capture_output=True,
                text=True,
                check=False,
                env=environment,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((dsh_home / ".agent-presets/ast-team/agent.cordis.yml").is_file())
            self.assertTrue((dsh_home / "profiles/web/cordis.patch.yml").is_file())

    def test_composition_parses_as_a_loader_entry_list(self) -> None:
        """The preset must be a named-row list; a bad composition is refused."""
        script = r"""
import { loadCatalog } from './bin/installer/catalog.mjs';
import { renderAdapterArtifacts } from './bin/adapters/dsh.mjs';
const catalog = loadCatalog(process.cwd());
const artifacts = renderAdapterArtifacts({
  packageRoot: process.cwd(),
  home: '/tmp/isolated-dsh-home',
  tool: catalog.tools.find((tool) => tool.id === 'dsh'),
  agents: catalog.agents,
  groups: {},
  specialists: [],
});
const preset = artifacts.find((a) => a.label === 'adapter:dsh/preset:composition');
process.stdout.write(String(preset.content));
"""
        result = run_node(script)
        self.assertEqual(result.returncode, 0, result.stderr)
        composition = result.stdout
        for row in (
            "- id: persona",
            "- id: agent-instructions",
            "- id: tool-skill",
            "- id: tool-subagent",
        ):
            self.assertIn(row, composition)
        # The host `skill-filesystem` row is patched, not duplicated here: a
        # second provider for the same root would collide. The name may appear
        # in comments, so check for an active row rather than the bare string.
        self.assertNotIn("- id: skill-filesystem", composition)
        self.assertNotIn("'@deepseek-ai/dsh-skill-filesystem'", composition)
        active = [
            line for line in composition.splitlines()
            if line and not line.lstrip().startswith("#")
        ]
        self.assertNotIn("skill-filesystem", "\n".join(active))
        # Every role must be routable by name from the persona.
        for agent in json.loads(
            (ROOT / "config" / "team-manifest.json").read_text(encoding="utf-8")
        )["agents"]:
            self.assertIn(f"`ast-{agent['id']}`", composition)


if __name__ == "__main__":
    unittest.main()
