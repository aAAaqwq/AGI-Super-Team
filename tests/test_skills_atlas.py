import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillsAtlasBuildTests(unittest.TestCase):
    def test_build_matches_the_canonical_catalog(self) -> None:
        catalog = json.loads(
            (ROOT / "catalog/skill-index.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "atlas"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "skills-atlas/scripts/build.py"),
                    "--out",
                    str(out),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("AGI Skills Atlas built", result.stdout)

            index = json.loads((out / "data/index.json").read_text(encoding="utf-8"))
            self.assertEqual(index["schema"], "agi-skills-atlas/v1")
            self.assertEqual(index["stats"]["total"], catalog["inventoryCount"])
            self.assertEqual(len(index["skills"]), catalog["inventoryCount"])
            self.assertEqual(len(index["categories"]), len(catalog["categories"]))
            self.assertGreater(index["stats"]["originals"], 0)

            first = index["skills"][0]
            for key in ("id", "category", "json_url", "path", "url"):
                self.assertIn(key, first)
            skill_payload = json.loads(
                (out / first["json_url"]).read_text(encoding="utf-8")
            )
            self.assertIn("content", skill_payload)
            self.assertEqual(skill_payload["id"], first["id"])

            self.assertIn("# AGI Skills Atlas", (out / "llms.txt").read_text(encoding="utf-8"))
            self.assertIn(
                "AGI Skills Atlas",
                (out / "index.html").read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                "{{TOTAL}}",
                (out / "index.html").read_text(encoding="utf-8"),
            )
            guide = (out / "for-agents.html").read_text(encoding="utf-8")
            self.assertIn("agent-prompt", guide)
            self.assertIn("data/index.json", guide)
            self.assertNotIn("{{TOTAL}}", guide)
            self.assertTrue((out / "assets/guide.js").is_file())
            self.assertIn(
                "for-agents.html",
                (out / "sitemap.xml").read_text(encoding="utf-8"),
            )
            tokens = (out / "assets/domain-tokens.css").read_text(encoding="utf-8")
            self.assertEqual(tokens.count("[data-domain="), len(catalog["categories"]))


if __name__ == "__main__":
    unittest.main()
