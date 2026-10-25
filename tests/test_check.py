"""Tests for scripts/check.py. Run: python3 -I -m unittest discover -s tests"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECK = ROOT / "scripts" / "check.py"


def run_check(site: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(CHECK), str(site)], capture_output=True, text=True)


class CheckScriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.site = self.tmp / "site"
        shutil.copytree(ROOT / "site", self.site)
        shutil.copytree(ROOT / ".github", self.tmp / ".github")
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_committed_site_passes(self):
        r = run_check(self.site)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_protocol_relative_url_in_html_fails(self):
        p = self.site / "index.html"
        p.write_text(p.read_text().replace("</head>", '<link rel="stylesheet" href="//fonts.googleapis.com/css?family=Lora">\n</head>'))
        r = run_check(self.site)
        self.assertEqual(r.returncode, 1)
        self.assertIn("//fonts.googleapis.com", r.stdout)

    def test_import_of_external_url_in_css_fails(self):
        p = self.site / "assets" / "css" / "style.css"
        p.write_text('@import url("https://fonts.googleapis.com/css?family=Lora");\n' + p.read_text())
        r = run_check(self.site)
        self.assertEqual(r.returncode, 1)
        self.assertIn("fonts.googleapis.com", r.stdout)

    def test_missing_font_file_referenced_from_css_fails(self):
        p = self.site / "assets" / "css" / "style.css"
        p.write_text(p.read_text().replace("manrope-600.woff2", "manrope-missing.woff2"))
        r = run_check(self.site)
        self.assertEqual(r.returncode, 1)
        self.assertIn("manrope-missing.woff2", r.stdout)


if __name__ == "__main__":
    unittest.main()
