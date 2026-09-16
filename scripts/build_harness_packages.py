"""Shared builder for the curated per-harness packages under ``plugins/``.

The curated packages are *generated*, exactly like
``plugins/agi-super-team-codex/payload/``. What makes them different is where
the bytes come from: instead of re-rendering each harness in Python, this
module shells out to ``scripts/util/render_harness_artifacts.mjs``, which calls
the very same ``renderAdapterArtifacts`` / ``buildConnectionSpec`` functions the
installer calls in ``bin/adapters/<harness>.mjs``. One renderer per harness --
this builder is not a second one.

Scope is deliberately narrow. A curated package ships the **harness-specific
layer** only: agent definitions, profiles, presets, connection specs. It does
not ship ``skills/``. Those are canonical content the installer vendors from
the single ``skills/`` root, and copying them into every package would
duplicate canonical source merely to satisfy a harness layout (ADR-0002). A
consumer that wants the Skill bodies runs the installer.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PATH = REPO_ROOT / "scripts" / "util" / "render_harness_artifacts.mjs"
PACKAGE_ROOT = Path("plugins")

# Stands in for the harness home. The adapters resolve absolute paths from
# ``home``; the bridge hands them a throwaway ``/tmp`` directory so the
# adapter path-safety guards are satisfied, and this builder rewrites that
# directory to ``.`` so the checked-in spec is package-relative. A spec that
# embedded a per-run temp path would differ on every machine and make
# ``--check`` useless.
PACKAGE_HOME = "."

# A distinctive token rather than `$version` or `{version}`: the templates are
# JSON and prose that legitimately contain `$VAR` shell references and `{}`
# braces, so a common-looking placeholder would be ambiguous.
VERSION_PLACEHOLDER = "@@VERSION@@"

# Stands in for the checkout path. DSH bakes the absolute repository root into
# its preset and orchestrator Skill ("canonical roles live at <path>/agents").
# A checked-in file may not carry one contributor's checkout location.
REPOSITORY_ROOT_PLACEHOLDER = "<repository-root>"


class BuilderError(RuntimeError):
    """A build step failed in a way the caller must surface, not swallow."""


@dataclass(frozen=True)
class HarnessPackage:
    """Everything a per-harness builder needs to know about its package.

    ``manifest_relative`` is the harness-native manifest that makes the package
    discoverable. It is the same file ``tests/test_distribution_release_contract.py``
    asserts ships in the published tarball, so it is declared once here and
    reused by both the builder and the test.
    """

    harness: str
    package: str
    manifest_relative: str
    manifest: str
    readme: str
    connection_relative: str
    notices: str = ""
    extra_outputs: dict[str, str] = field(default_factory=dict)

    @property
    def plugin_root(self) -> Path:
        return PACKAGE_ROOT / self.package


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def release_version(root: Path) -> str:
    return _load_json(root / "package.json")["version"]


def render_harness(harness: str, root: Path) -> dict[str, Any]:
    """Run the Node bridge and return its parsed payload.

    The bridge is the only supported way to obtain these bytes: if it fails the
    build fails loudly rather than quietly falling back to a hand-written
    renderer that would then drift from ``bin/adapters/``.
    """

    completed = subprocess.run(
        ["node", str(BRIDGE_PATH), "--root", str(root), "--harness", harness],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise BuilderError(
            f"harness renderer failed for {harness}:\n"
            f"{completed.stdout}{completed.stderr}"
        )
    return json.loads(completed.stdout)


def _rebind_home(value: Any, home: str, replacement: str) -> Any:
    if isinstance(value, dict):
        return {key: _rebind_home(item, home, replacement) for key, item in value.items()}
    if isinstance(value, list):
        return [_rebind_home(item, home, replacement) for item in value]
    if isinstance(value, str):
        if value == home:
            return replacement
        if value.startswith(f"{home}/"):
            return f"{replacement}{value[len(home):]}"
    return value


def normalize_connection(
    connection: dict[str, Any],
    home: str,
    harness: str,
    plugin_root_posix: str,
) -> dict[str, Any]:
    """Rewrite the adapter's connection spec so its paths are package-relative.

    The envelope below mirrors ``bin/installer/core.mjs`` exactly: the installer
    also overrides ``harness`` with the tool id and defaults the coordinator
    fields, and a package that disagreed with the installer about the same
    document would be worse than no package. The two additions are
    ``packageRoot`` (the installer has a real home; a package does not) and
    ``generatedBy``.
    """

    rebased = _rebind_home(connection, home, PACKAGE_HOME)
    return {
        **rebased,
        "schemaVersion": 1,
        "harness": harness,
        "runtimeEvidence": "pending",
        "packageRoot": plugin_root_posix,
        "coordinator": rebased.get("coordinator", "ast-ceo"),
        "independentReviewer": rebased.get("independentReviewer", "ast-governor"),
        "requiredMaxDepth": rebased.get("requiredMaxDepth", 2),
        "maxConcurrentChildren": rebased.get("maxConcurrentChildren", 2),
        "generatedBy": "scripts/build_harness_packages.py",
    }


def _substitute(template: str, version: str) -> str:
    """Fill the version placeholder.

    A literal replacement, not ``str.format`` or ``string.Template``: the
    templates are JSON manifests and prose that freely mentions shell variables
    (``$DSH_PROFILE``, ``$HERMES_HOME``), and both of those mini-languages
    would treat those characters as syntax.
    """

    return template.replace(VERSION_PLACEHOLDER, version)


def _starter_files(
    package: HarnessPackage, root: Path, version: str
) -> dict[Path, str]:
    """Files that do not come from the adapter: manifest, README, notices."""

    outputs = {
        root
        / package.plugin_root
        / package.manifest_relative: _substitute(package.manifest, version),
        root / package.plugin_root / "README.md": _substitute(package.readme, version),
    }
    if package.notices:
        outputs[
            root / package.plugin_root / "THIRD_PARTY_NOTICES.md"
        ] = _substitute(package.notices, version)
    for relative, template in package.extra_outputs.items():
        outputs[root / package.plugin_root / relative] = _substitute(template, version)
    return outputs


def _directories_owned_by_adapter(artifact_paths: list[Path]) -> list[Path]:
    """Every directory an artifact lives in, including the package root.

    The package root is included because artifacts at the top level would
    otherwise have no directory watched, and a stale sibling of them would go
    undetected. Paths are compared in their raw form: the adapters join
    relative segments, and ``Path('.')`` normalization would collapse the
    ``.agent-presets`` prefix that the artifact paths legitimately carry.
    """

    directories: set[str] = {"."}
    for relative in artifact_paths:
        parts = relative.as_posix().split("/")[:-1]
        for index in range(1, len(parts) + 1):
            directories.add("/".join(parts[:index]))
    return [Path(name) for name in sorted(directories)]


def _stabilize(text: str, home: str, root: Path) -> str:
    """Remove every machine-specific absolute path from generated content.

    Two distinct paths leak in, both from the adapters doing what they are
    supposed to do when the installer drives them:

    * ``home`` -- the harness root. The bridge hands the adapters a throwaway
      temp directory so their path-safety guards pass, and Hermes records it in
      each profile blueprint's ``roleSkill``.
    * the repository root -- DSH notes which checkout the canonical agents came
      from, so the preset carries the absolute source path.

    Neither may survive into a checked-in file: the bytes would differ per
    machine and per run, and ``--check`` would fail for every contributor whose
    checkout is not at the original path. Both are rewritten to package- or
    repository-relative references.
    """

    for candidate in {str(root), os.path.realpath(root)}:
        text = text.replace(candidate, REPOSITORY_ROOT_PLACEHOLDER)
    text = text.replace(home, PACKAGE_HOME)
    # `home` resolves to a bare `.`, so `$DSH_HOME/skills` becomes
    # `./.dsh/skills` while the patched `customSkillDirs` entry names the same
    # directory `./skills`. One spelling, or the package contradicts itself.
    text = text.replace("./.dsh/skills", "./skills")
    # GitHub flags a missing final newline on every diff. Match the Codex
    # payload, which ends with one.
    if not text.endswith("\n"):
        text += "\n"
    return text


def build_outputs(package: HarnessPackage, root: Path) -> dict[Path, str]:
    """Return every generated path for one package mapped to its content."""

    payload = render_harness(package.harness, root)
    outputs = _starter_files(package, root, release_version(root))
    home = payload["home"]

    for artifact in payload["artifacts"]:
        relative = Path(artifact["relativePath"])
        path = root / package.plugin_root / relative
        if path in outputs:
            raise BuilderError(
                f"{package.package}: adapter artifact collides with a starter file: {relative}"
            )
        outputs[path] = _stabilize(
            base64.b64decode(artifact["contentBase64"]).decode("utf-8"), home, root
        )

    connection = normalize_connection(
        payload["connection"], home, package.harness, package.plugin_root.as_posix()
    )
    outputs[root / package.plugin_root / package.connection_relative] = _stabilize(
        json.dumps(connection, indent=2, ensure_ascii=False) + "\n", home, root
    )
    return outputs


def _stray_files(package: HarnessPackage, root: Path, expected: set[Path]) -> list[Path]:
    """Generated-looking files under an adapter-owned directory that no longer
    belong.

    Mirrors the Codex builder's "unexpected generated agent" guard: renaming a
    role upstream must not silently leave a stale artifact behind in the
    package, where it would look installable and be wrong.
    """

    plugin_root = root / package.plugin_root
    if not plugin_root.is_dir():
        return []
    payload = render_harness(package.harness, root)
    directories = _directories_owned_by_adapter(
        [Path(artifact["relativePath"]) for artifact in payload["artifacts"]]
    )
    strays: set[Path] = set()
    for relative in directories:
        directory = plugin_root / relative
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            if path.absolute() not in expected:
                strays.add(path)
    return sorted(strays)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def build(root: Path, package: HarnessPackage, check: bool) -> int:
    """Write (or verify) one package. Returns a process exit code."""

    outputs = build_outputs(package, root)
    expected = {path.absolute() for path in outputs}
    stale = [
        path
        for path, content in outputs.items()
        if path.is_symlink()
        or not path.is_file()
        or path.read_text(encoding="utf-8") != content
    ]
    strays = _stray_files(package, root, expected)

    if check:
        for path in stale:
            print(f"{package.package} package is stale: {path.relative_to(root)}")
        for path in strays:
            print(f"Unexpected generated artifact: {path.relative_to(root)}")
        return 1 if stale or strays else 0

    for path in stale:
        _atomic_write(path, outputs[path])
        print(f"Wrote {path.relative_to(root)}")
    if strays:
        raise BuilderError(
            "remove obsolete generated artifacts explicitly: "
            + ", ".join(str(path.relative_to(root)) for path in strays)
        )
    return 0


def make_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the generated package is current without writing",
    )
    return parser


def main(package: HarnessPackage, description: str) -> int:
    """Entry point for the per-harness builders in ``scripts/``.

    One package per invocation. ``scripts/check_harness_packages.py`` is the
    aggregate entry point, so a builder never needs to know about its siblings.
    """

    parser = make_parser(description)
    arguments = parser.parse_args()
    return build(arguments.root.resolve(), package, arguments.check)


@dataclass(frozen=True)
class RegisteredPackage:
    """A package and the builder script that generates it."""

    package: HarnessPackage
    builder: Path


def registered_packages(root: Path = REPO_ROOT) -> list[RegisteredPackage]:
    """Every per-harness builder, discovered from the modules in ``scripts/``.

    The builders are found rather than listed, so adding one cannot leave the
    aggregate check silently covering three of four packages -- the failure mode
    where the newest package is the one nothing verifies.
    """

    packages = []
    for path in sorted(root.glob("scripts/build_*_package.py")):
        module = _load_builder_module(path)
        package = getattr(module, "PACKAGE", None)
        if isinstance(package, HarnessPackage):
            packages.append(RegisteredPackage(package=package, builder=path))
    return packages


def _load_builder_module(path: Path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(f"_ast_builder_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise BuilderError(f"cannot load builder module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
