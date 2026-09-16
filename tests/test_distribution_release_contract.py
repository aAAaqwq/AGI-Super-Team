import json
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Every curated distribution package, and the manifest that makes it
# discoverable by its harness. Kept in lockstep with config/repository-architecture.json
# and plugins/README.md.
#
# A package belongs here only when it ships real components. A manifest that
# installs nothing overstates compatibility, so packages without content are
# removed rather than kept as placeholders (ADR-0006).
DISTRIBUTION_MANIFESTS = {
    "agi-super-team-codex": ".codex-plugin/plugin.json",
}

# Harness entries that live at the repository root rather than inside a curated
# package. A harness reads these to discover the checkout without cloning it, so
# each one must survive `npm pack` or the package only installs on the harnesses
# whose entry happens to be listed.
#
# Only directories holding machine-readable install config belong here. A
# directory carrying a human guide alone installs nothing, so it overstates
# compatibility and is excluded (same rule as ADR-0006 for plugins/).
ROOT_HARNESS_MANIFESTS = {
    ".agents": (".agents/plugins/marketplace.json",),
    ".claude-plugin": (
        ".claude-plugin/marketplace.json",
        ".claude-plugin/plugin.json",
    ),
    ".cursor-plugin": (".cursor-plugin/plugin.json",),
    ".kimi-plugin": (".kimi-plugin/plugin.json",),
}

# Root-level harness entries that are single files rather than directories.
ROOT_HARNESS_DESCRIPTORS = (
    "gemini-extension.json",
    # Human-facing Codex install guide, shipped because README*/STARTUP.md/
    # setup.md link to .codex/INDEX.md and npm consumers would otherwise follow
    # those links into a missing path. Codex installs from
    # plugins/agi-super-team-codex, so this file needs no install config.
    ".codex/INDEX.md",
)


def _packed_tarball() -> dict:
    """Return the parsed `npm pack --dry-run` payload for this checkout."""
    result = subprocess.run(
        ["npm", "pack", "--dry-run", "--json", "--ignore-scripts"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"npm pack failed:\n{result.stdout}{result.stderr}")
    return json.loads(result.stdout)[0]


def _packed_tarball_paths() -> set[str]:
    """Return the paths npm would actually publish."""
    return {entry["path"] for entry in _packed_tarball()["files"]}


def _glob_matches_published(pattern: str, published: set[str]) -> bool:
    """Match an npm `files` glob against published paths, not the filesystem.

    Uses `fnmatch` translation over the *tarball* paths. `Path.glob` cannot be
    used: `Path.glob("a/*/b/**")` needs every intermediate directory to exist
    on the running machine, so the same commit can pass locally and fail in CI
    while npm packs the content correctly either way. `**` is translated to
    match across separators; a single `*` stays within one path segment.
    """
    translated = re.escape(pattern)
    translated = translated.replace(r"\*\*/", ".*/").replace(r"\*\*", ".*")
    translated = translated.replace(r"\*", "[^/]*")
    regex = re.compile(f"^{translated}$")
    return any(regex.match(path) for path in published)


class DistributionReleaseContractTests(unittest.TestCase):
    def test_npm_tarball_contains_the_runtime_and_no_transient_files(self) -> None:
        files = {entry["path"]: entry for entry in _packed_tarball()["files"]}

        required_runtime = {
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "bin").rglob("*.mjs")
        }
        self.assertTrue(required_runtime <= files.keys())
        self.assertEqual(files["bin/agi-super-team.mjs"]["mode"] & 0o111, 0o111)
        self.assertFalse(
            any(
                "__pycache__" in path
                or path.endswith((".pyc", ".pyo", ".DS_Store", ".env"))
                for path in files
            )
        )

    def test_npm_and_codex_plugin_versions_are_identical(self) -> None:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        plugin = json.loads(
            (
                ROOT
                / "plugins"
                / "agi-super-team-codex"
                / ".codex-plugin"
                / "plugin.json"
            ).read_text(encoding="utf-8")
        )

        self.assertRegex(package["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(plugin["version"], package["version"])

    def test_every_distribution_package_ships_a_manifest_in_the_tarball(self) -> None:
        published = _packed_tarball_paths()
        for package, manifest in DISTRIBUTION_MANIFESTS.items():
            with self.subTest(package=package):
                relative = f"plugins/{package}/{manifest}"
                self.assertTrue(
                    (ROOT / relative).is_file(),
                    f"{relative} must exist on disk",
                )
                self.assertIn(
                    relative,
                    published,
                    f"{relative} must be published, not only present in the checkout",
                )

    def test_distribution_packages_share_the_release_version(self) -> None:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        for name, manifest in DISTRIBUTION_MANIFESTS.items():
            with self.subTest(package=name):
                document = json.loads(
                    (ROOT / "plugins" / name / manifest).read_text(encoding="utf-8")
                )
                self.assertEqual(
                    document["version"],
                    package["version"],
                    f"{name} must track the npm release version",
                )

    def test_codex_marketplace_install_never_tracks_a_mutable_branch(self) -> None:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        cli = (ROOT / "bin" / "agi-super-team.mjs").read_text(encoding="utf-8")
        shell_installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        guide = (ROOT / "docs" / "guides" / "codex-install.html").read_text(
            encoding="utf-8"
        )

        self.assertNotIn('"--ref", "main"', cli)
        self.assertNotIn("git pull", shell_installer)
        self.assertIn(f'REPO_REF="${{AGI_SUPER_TEAM_REF:-v{package["version"]}}}"', shell_installer)
        self.assertNotIn("--ref main", guide)
        self.assertIn(f"v{package['version']}", guide)

    def test_every_root_harness_entry_ships_in_the_npm_tarball(self) -> None:
        """A harness entry missing from `files` silently drops that harness.

        `files` is an allowlist, so a root entry that is never listed is absent
        from the published tarball even though it is present in the checkout.
        The install promise is per-harness, so each entry is asserted
        individually rather than as one aggregate.
        """
        published = _packed_tarball_paths()

        for directory, manifests in ROOT_HARNESS_MANIFESTS.items():
            # Adding a file to a harness directory must not require remembering
            # to extend `files`; every file that is there has to travel with it.
            expected = set(manifests)
            expected |= {
                path.relative_to(ROOT).as_posix()
                for path in (ROOT / directory).rglob("*")
                if path.is_file()
            }
            for entry in sorted(expected):
                with self.subTest(entry=entry):
                    self.assertTrue((ROOT / entry).is_file(), f"{entry} must exist on disk")
            missing = sorted(expected - published)
            self.assertEqual(
                missing,
                [],
                f"files in {directory} are missing from the published tarball: {missing}",
            )

        for descriptor in ROOT_HARNESS_DESCRIPTORS:
            with self.subTest(entry=descriptor):
                self.assertTrue((ROOT / descriptor).is_file(), f"{descriptor} must exist on disk")
        missing = sorted(set(ROOT_HARNESS_DESCRIPTORS) - published)
        self.assertEqual(
            missing,
            [],
            f"root harness entries are missing from the published tarball: {missing}",
        )

    def test_no_files_entry_silently_matches_nothing(self) -> None:
        """A `files` entry that matches no file drops content without a warning.

        `files` is an allowlist, so a no-match entry is invisible: the tarball
        still builds and still looks healthy. This shipped no `agents` and no
        `references` for the Codex plugin until it was caught.

        Two traps are covered. A wildcard ending in `/` makes npm publish
        nothing at all, because npm does not recurse the way a directory
        walker does -- only `**` reaches the contents. And a wildcard that
        simply matches no file today silently drops that content.

        `!` entries are exclusions rather than content, so matching nothing is
        their healthy state.

        Non-`!` entries are judged by what the *tarball* actually contains,
        not by `Path.glob`. `Path.glob("a/*/b/**")` requires every intermediate
        directory to exist on the running machine, so it can report "no match"
        for a pattern that npm packs correctly -- a difference that made this
        test pass locally and fail in CI on the same commit. The tarball is the
        artifact under test, so it is the artifact that gets inspected.
        """
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        published = _packed_tarball_paths()

        for entry in package["files"]:
            if entry.startswith("!"):
                continue
            with self.subTest(entry=entry):
                if "*" not in entry:
                    self.assertTrue(
                        (ROOT / entry).exists(),
                        f'files entry "{entry}" does not exist and ships no content',
                    )
                    # Directories are never listed as tarball entries themselves;
                    # they contribute their contents. Files are listed verbatim.
                    if (ROOT / entry).is_dir():
                        prefix = entry.rstrip("/") + "/"
                        self.assertTrue(
                            any(path.startswith(prefix) for path in published),
                            f'files entry "{entry}" is a directory that ships nothing',
                        )
                    else:
                        self.assertIn(
                            entry,
                            published,
                            f'files entry "{entry}" exists but reaches no published path',
                        )
                    continue
                self.assertFalse(
                    entry.endswith("/"),
                    f'files entry "{entry}" is a wildcard ending in "/", which npm '
                    f'publishes as nothing; write "{entry.rstrip("/")}/**" instead',
                )
                self.assertTrue(
                    _glob_matches_published(entry, published),
                    f'files entry "{entry}" matches no file and ships no content',
                )

    def test_ci_covers_supported_node_releases_and_primary_harnesses(self) -> None:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        workflow = (
            ROOT / ".github" / "workflows" / "validate-repository.yml"
        ).read_text(encoding="utf-8")
        packed_smoke = (ROOT / "tests" / "windows_cli_smoke.mjs").read_text(
            encoding="utf-8"
        )

        self.assertEqual(package["engines"]["node"], ">=18")
        for version in ("18", "20", "22", "24"):
            with self.subTest(node=version):
                self.assertRegex(workflow, rf'["\']{re.escape(version)}["\']')
        for harness in ("claude-code", "codex", "openclaw", "hermes"):
            with self.subTest(harness=harness):
                self.assertIn(harness, packed_smoke)
        for runner in ("ubuntu-latest", "macos-latest", "windows-latest"):
            with self.subTest(runner=runner):
                self.assertIn(runner, workflow)


if __name__ == "__main__":
    unittest.main()
