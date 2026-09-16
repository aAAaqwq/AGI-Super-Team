import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_MARKDOWN = (
    "README.md",
    "README_CN.md",
    "README.es-ES.md",
    "ARCHITECTURE.md",
    "CONTEXT.md",
    "AGENTS.md",
    "STARTUP.md",
    "CLAUDE.md",
    "skills/README.md",
    "starter-kits/README.md",
    "cookbook/README.md",
    "plugins/README.md",
    "plugins/agi-super-team-codex/README.md",
    "plugins/agi-super-team-claudecode/README.md",
    "plugins/agi-super-team-hermes/README.md",
    "plugins/agi-super-team-dsh/README.md",
    "plugins/agi-super-team-openclaw/README.md",
    "config/README.md",
    "scripts/README.md",
    "tests/README.md",
    "docs/README.md",
    "docs/adr/README.md",
    # Maintained docs trees. Added after a docs/ restructure broke relative
    # links in files that were not on this list — the contract only guards
    # what it enumerates, so new curated trees must be added here.
    "docs/architecture/repository-architecture.md",
    "docs/architecture/adapter-registration.md",
    "docs/architecture/repository-entrypoints.md",
    "docs/researchs/README.md",
    "docs/researchs/coding-agent-assembly.md",
    "docs/researchs/adapter-codex.md",
    "docs/researchs/adapter-claude-code.md",
    "docs/researchs/adapter-openclaw.md",
    "docs/researchs/adapter-hermes.md",
    "docs/researchs/adapter-kimi.md",
    "docs/researchs/adapter-dsh.md",
    "docs/plans/README.md",
    "docs/plans/dsh-primary-adapter.md",
    "docs/reference/docs-inventory.md",
)
MARKDOWN_LINK = re.compile(r"!?\[[^]]*\]\(([^)]+)\)")


class NavigationContractTests(unittest.TestCase):
    def test_curated_markdown_relative_links_resolve(self) -> None:
        for relative in PUBLIC_MARKDOWN:
            source = ROOT / relative
            text = source.read_text(encoding="utf-8")
            for target in MARKDOWN_LINK.findall(text):
                target = target.strip().split(maxsplit=1)[0].strip("<>")
                if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                    continue
                route, _, fragment = target.partition("#")
                path = (source.parent / route).resolve()
                with self.subTest(source=relative, target=target):
                    self.assertTrue(path.exists())
                    if fragment:
                        index = path / "README.md" if path.is_dir() else path
                        content = index.read_text(encoding="utf-8")
                        self.assertIn(f'id="{fragment}"', content)

    def test_language_and_distribution_routes_are_bidirectional(self) -> None:
        english = (ROOT / "README.md").read_text(encoding="utf-8")
        chinese = (ROOT / "README_CN.md").read_text(encoding="utf-8")
        spanish = (ROOT / "README.es-ES.md").read_text(encoding="utf-8")
        self.assertIn("./README_CN.md", english)
        self.assertIn("./README.es-ES.md", english)
        self.assertIn("./README.md", chinese)
        self.assertIn("./README.es-ES.md", chinese)
        self.assertIn("./README.md", spanish)
        self.assertIn("./README_CN.md", spanish)
        for text in (english, chinese, spanish):
            self.assertIn("docs/guides/claude-code-install.html", text)
            self.assertIn("docs/guides/harness-compatibility.html", text)

    def test_curated_entrypoints_reject_legacy_install_commands(self) -> None:
        forbidden = (
            "openclaw gateway start",
            "openclaw gateway restart",
            "cp -r skills/",
            "ln -s $(pwd)/skills/",
            "skills/categories/README.md",
        )
        for relative in PUBLIC_MARKDOWN:
            text = (ROOT / relative).read_text(encoding="utf-8")
            for value in forbidden:
                with self.subTest(source=relative, forbidden=value):
                    self.assertNotIn(value, text)


if __name__ == "__main__":
    unittest.main()
