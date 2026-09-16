"""Shared fixture and registry for the per-harness curated package tests.

The package registry itself lives in ``scripts/build_harness_packages.py``,
which discovers a ``PACKAGE`` declaration in each ``scripts/build_*_package.py``.
This module re-exports it rather than restating it, so a new package cannot be
registered in production and forgotten in the tests -- the reverse of the usual
drift.

The fixture builds a *minimal* repository rather than copying the real one: the
adapters read ``config/``, ``agents/``, the Codex plugin's payload, and the
Skill directories named in the team manifest, so the fixture carries exactly
those. A full copy would be ~90 MB per test process; the fixture is ~5 MB and
makes the same assertion, because every path is resolved relative to ``--root``.
"""

from __future__ import annotations

import base64
import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

# Discovered by `unittest discover -s tests`, which puts this directory on
# sys.path, so the test modules import it by bare name.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_harness_packages import (  # noqa: E402
    HarnessPackage,
    registered_packages,
)

MANIFEST_KEYS = ("required", "optional", "harnessSpecific")


@dataclass(frozen=True)
class PackageSpec:
    """One curated distribution package."""

    harness: str
    package: str
    builder: str
    manifest: str

    @property
    def plugin_root(self) -> Path:
        return ROOT / "plugins" / self.package

    @property
    def builder_path(self) -> Path:
        return ROOT / self.builder

    @property
    def manifest_path(self) -> Path:
        return self.plugin_root / self.manifest


def _specs() -> tuple[PackageSpec, ...]:
    return tuple(
        PackageSpec(
            harness=entry.package.harness,
            package=entry.package.package,
            builder=entry.builder.relative_to(ROOT).as_posix(),
            manifest=entry.package.manifest_relative,
        )
        for entry in registered_packages(ROOT)
    )


PACKAGES: tuple[PackageSpec, ...] = _specs()

BY_HARNESS = {spec.harness: spec for spec in PACKAGES}


def _manifest_skill_names() -> set[str]:
    manifest = json.loads(
        (ROOT / "config/team-manifest.json").read_text(encoding="utf-8")
    )
    names: set[str] = set()
    for agent in manifest["agents"]:
        for key in MANIFEST_KEYS:
            names.update(agent.get("skills", {}).get(key, []))
    return names


def _copy_tree(relative: str, destination: Path) -> None:
    shutil.copytree(ROOT / relative, destination / relative)


@contextlib.contextmanager
def minimal_repository() -> Iterator[Path]:
    """Yield a temporary repository that renders the same bytes as this one.

    Only the inputs the builders actually read are copied, so the fixture stays
    small enough to build per test case. The Skill directories are stubbed to
    their ``SKILL.md`` because the adapters vendor directories but the curated
    packages deliberately do not contain them -- so a stub proves the same
    thing as the full tree.
    """

    with tempfile.TemporaryDirectory(prefix="ast-package-fixture-") as temporary:
        root = Path(temporary)
        for relative in ("config", "agents", "bin"):
            _copy_tree(relative, root)
        (root / "scripts").mkdir(parents=True, exist_ok=True)
        _copy_tree("scripts/util", root)
        # The DSH and Codex adapters read the Codex plugin's curated Skill tree
        # and global CEO payload; both are small and are real inputs.
        _copy_tree("plugins/agi-super-team-codex/skills", root)
        _copy_tree("plugins/agi-super-team-codex/payload/global", root)
        (root / "package.json").write_text(
            (ROOT / "package.json").read_text(encoding="utf-8"), encoding="utf-8"
        )
        for name in _manifest_skill_names():
            source = ROOT / "skills" / name / "SKILL.md"
            if not source.is_file():
                continue
            destination = root / "skills" / name / "SKILL.md"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        yield root


def run_builder(spec: PackageSpec, root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Invoke a package builder against ``root``."""

    return subprocess.run(
        [sys.executable, str(spec.builder_path), "--root", str(root), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def render_artifacts(root: Path, harness: str) -> dict:
    """Call the Node bridge directly. The single renderer, not a re-implementation."""

    completed = subprocess.run(
        [
            "node",
            str(ROOT / "scripts/util/render_harness_artifacts.mjs"),
            "--root",
            str(root),
            "--harness",
            harness,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(f"bridge failed for {harness}: {completed.stderr}")
    return json.loads(completed.stdout)


def expected_artifact_text(artifact: dict, home: str, root: Path) -> str:
    """The text a package file must hold, from the adapter's raw bytes.

    This restates the builder's path stabilization as an *independent* oracle.
    Deriving it here, from the adapter's own output, is what makes the
    byte-for-byte test meaningful: if the builder ever grew a second renderer,
    the package would stop matching the adapter and this would fail rather than
    agree with the duplicated logic.

    The adjustments are the two the builder documents, and nothing else:

    * the repository root and the harness home, both of which the adapters bake
      into content when the installer drives them;
    * one spelling for the DSH skills directory (``./.dsh/skills`` and
      ``./skills`` name the same directory once ``home`` resolves to ``.``);
    * a trailing newline, matching the Codex payload convention.
    """

    text = base64.b64decode(artifact["contentBase64"]).decode("utf-8")
    for candidate in {str(root), os.path.realpath(root)}:
        text = text.replace(candidate, "<repository-root>")
    text = text.replace(home, ".")
    text = text.replace("./.dsh/skills", "./skills")
    if not text.endswith("\n"):
        text += "\n"
    return text


class PackageConformanceTests:
    """Assertions every curated package has to satisfy.

    Subclass per harness and set ``SPEC``. The harness-specific test files add
    what only that harness needs on top.
    """

    SPEC: PackageSpec
    maxDiff = None

    def test_generated_package_is_current(self) -> None:
        """The checked-in package matches its generator.

        Without this the build is a suggestion: sources move, nobody reruns the
        builder, and the shipped artifacts silently describe an older harness
        contract. This is the assertion that keeps the two in step.
        """

        result = run_builder(self.SPEC, ROOT, "--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_package_is_what_the_harness_adapter_renders(self) -> None:
        """Byte-for-byte against the adapter, from a different repository root.

        Two things are proven at once. Building in a temporary root and
        comparing to the checked-in bytes shows the package is not
        root-dependent; comparing against the adapter's own output shows the
        package is *that renderer's* product, not a parallel implementation.
        """

        with minimal_repository() as fixture_root:
            payload = render_artifacts(fixture_root, self.SPEC.harness)
            for artifact in payload["artifacts"]:
                relative = artifact["relativePath"]
                with self.subTest(artifact=relative):
                    packaged = self.SPEC.plugin_root / relative
                    self.assertTrue(packaged.is_file(), f"{relative} is not in the package")
                    self.assertEqual(
                        packaged.read_text(encoding="utf-8"),
                        expected_artifact_text(
                            artifact, payload["home"], fixture_root
                        ),
                    )

    def test_check_rejects_a_hand_edited_artifact(self) -> None:
        """`--check` is not vacuous: a drifted artifact turns it red."""

        with minimal_repository() as fixture_root:
            self.assertEqual(
                run_builder(self.SPEC, fixture_root).returncode,
                0,
                "fixture build must succeed before the drift can be tested",
            )
            payload = render_artifacts(fixture_root, self.SPEC.harness)
            target = (
                fixture_root
                / "plugins"
                / self.SPEC.package
                / payload["artifacts"][0]["relativePath"]
            )
            target.write_text("# hand-edited\n", encoding="utf-8")

            checked = run_builder(self.SPEC, fixture_root, "--check")

            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("is stale", checked.stdout + checked.stderr)

    def test_check_rejects_an_unexpected_leftover_artifact(self) -> None:
        """A role renamed upstream must not leave an installable-looking stray."""

        with minimal_repository() as fixture_root:
            self.assertEqual(
                run_builder(self.SPEC, fixture_root).returncode,
                0,
                "fixture build must succeed before the stray can be tested",
            )
            payload = render_artifacts(fixture_root, self.SPEC.harness)
            artifact = Path(payload["artifacts"][0]["relativePath"])
            stray = (
                fixture_root
                / "plugins"
                / self.SPEC.package
                / artifact.parent
                / "ast-obsolete-role.md"
            )
            stray.parent.mkdir(parents=True, exist_ok=True)
            stray.write_text("# Obsolete\n", encoding="utf-8")

            checked = run_builder(self.SPEC, fixture_root, "--check")

            self.assertNotEqual(checked.returncode, 0)
            self.assertIn(
                "Unexpected generated artifact", checked.stdout + checked.stderr
            )

    def test_package_ships_no_canonical_skill_bodies(self) -> None:
        """ADR-0002: canonical content is not duplicated to satisfy a layout.

        The Skill directories the team manifest assigns to agents are canonical
        and belong to the installer, which vendors them from the single
        ``skills/`` root. A package that copied them would quadruple that tree.
        The generated orchestrator entry Skill is not one of them and is
        expected -- without it the package has no entry point.
        """

        canonical = _manifest_skill_names()
        offenders = [
            path.relative_to(self.SPEC.plugin_root).as_posix()
            for path in self.SPEC.plugin_root.rglob("SKILL.md")
            if path.parent.name in canonical
        ]
        self.assertEqual(offenders, [], "canonical Skill bodies must not be vendored")

    def test_manifest_tracks_the_release_version(self) -> None:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        document = json.loads(self.SPEC.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(document["version"], package["version"])

    def test_no_machine_specific_paths(self) -> None:
        """A checked-in artifact may not carry the builder's checkout or temp dir.

        Both leak naturally: the adapters record an absolute harness home, and
        DSH records which checkout the canonical agents came from. Either one
        makes the file differ per machine and per run.
        """

        offenders = []
        for path in sorted(self.SPEC.plugin_root.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            text = path.read_text(encoding="utf-8")
            for marker in ("/private/tmp/", "/tmp/agi-super-team-package-home", str(ROOT)):
                if marker in text:
                    offenders.append(
                        f"{path.relative_to(self.SPEC.plugin_root)} contains {marker}"
                    )
        self.assertEqual(offenders, [])

    def test_connection_spec_does_not_claim_runtime_evidence(self) -> None:
        """Structure is proven; client loading is not. The spec must say so."""

        connections = sorted(self.SPEC.plugin_root.rglob("connection.json"))
        self.assertEqual(len(connections), 1, "a package carries exactly one connection spec")
        spec = json.loads(connections[0].read_text(encoding="utf-8"))
        self.assertEqual(spec["harness"], self.SPEC.harness)
        self.assertEqual(spec["runtimeEvidence"], "pending")
        self.assertEqual(spec["coordinator"], "ast-ceo")
        self.assertEqual(spec["independentReviewer"], "ast-governor")
        self.assertLessEqual(
            spec["maxConcurrentChildren"],
            spec["requiredMaxDepth"] * 2,
            "concurrency must not exceed what depth 2 can carry",
        )

    def test_builder_holds_no_rendering_logic_of_its_own(self) -> None:
        """A second renderer is the failure mode this whole design avoids.

        If the shared builder ever learned what a Claude Code agent or a Hermes
        profile looks like, the adapters would stop being the single source of
        truth for their harness. These markers are the adapters' own envelope
        text; none of them belongs in generic builder code.
        """

        shared = (ROOT / "scripts" / "build_harness_packages.py").read_text(
            encoding="utf-8"
        )
        for marker in (
            "Claude Code 执行约束",
            "metadata:",
            "hermes:",
            "cordis",
            "sessions_spawn",
            "frontmatter",
            "disallowedTools",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, shared)
        self.assertIn("render_harness_artifacts.mjs", shared)
