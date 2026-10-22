# Copyright 2026 Workloom Solutions Private Limited
# SPDX-License-Identifier: MIT
"""
Unit tests for report.py. All of this is pure file parsing — no network,
no dependency on scanner_core. report.py reads the coverage tier with
write_reference's reader.

Run: python3 -m unittest discover -s tests
"""

import _guard  # noqa: F401  (first: isolates HOME, keys and network)
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import report

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "examples")
EXAMPLE_BANK = os.path.join(EXAMPLES_DIR, "content-signal-bank.example.jsonl")


class TestLoadBank(unittest.TestCase):
    def test_loads_the_bundled_example(self):
        rows = report.load_bank(EXAMPLE_BANK)
        self.assertEqual(len(rows), 3)
        sources = {r["source"] for r in rows}
        self.assertEqual(sources, {"hn", "reddit", "competitor_blog"})

    def test_missing_file_returns_empty_list_not_a_crash(self):
        self.assertEqual(report.load_bank("/definitely/not/a/real/bank.jsonl"), [])


class TestLoadThemes(unittest.TestCase):
    def test_loads_the_bundled_example_theme_doc(self):
        themes = report.load_themes(EXAMPLES_DIR)
        self.assertEqual(len(themes), 1)
        self.assertEqual(themes[0]["status"], "approved")
        self.assertEqual(themes[0]["coverage_tier"], "STRONG")

    def test_missing_dir_returns_empty_list_not_a_crash(self):
        self.assertEqual(report.load_themes("/definitely/not/a/real/dir"), [])


class TestRender(unittest.TestCase):
    def test_renders_source_counts_and_theme_counts(self):
        rows = report.load_bank(EXAMPLE_BANK)
        themes = report.load_themes(EXAMPLES_DIR)
        out = io.StringIO()
        report.render(rows, themes, out=out)
        text = out.getvalue()
        self.assertIn("Total rows: 3", text)
        self.assertIn("hn", text)
        self.assertIn("Total: 1", text)
        self.assertIn("approved", text)
        self.assertNotIn("%%", text)  # a percent sign renders once, not doubled

    def test_spent_and_unspent_are_counted_per_source(self):
        rows = [
            {"source": "hn", "theme_id": "theme-1"},
            {"source": "hn", "theme_id": None},
            {"source": "reddit", "theme_id": None},
        ]
        out = io.StringIO()
        report.render(rows, [], out=out)
        text = out.getvalue()
        self.assertIn("Total rows: 3 (2 un-spent, 1 spent)", text)
        self.assertRegex(text, r"hn\s+1 /\s+2\s+50%")
        self.assertRegex(text, r"reddit\s+0 /\s+1\s+0%")

    def test_empty_input_suggests_quickstart_not_a_blank_screen(self):
        out = io.StringIO()
        report.render([], [], out=out)
        text = out.getvalue()
        self.assertIn("quickstart", text)


class TestMissingPathsAreNamed(unittest.TestCase):
    def _main(self, *argv):
        from unittest import mock

        out = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["report.py", *argv]),
            mock.patch.object(sys, "stdout", out),
        ):
            report.main()
        return out.getvalue()

    def test_a_missing_bank_is_reported_as_missing_not_as_empty(self):
        text = self._main("--bank", "/nope/bank.jsonl", "--themes-dir", EXAMPLES_DIR)
        self.assertIn("no signal bank at /nope/bank.jsonl", text)

    def test_a_missing_themes_dir_is_reported(self):
        text = self._main("--bank", EXAMPLE_BANK, "--themes-dir", "/nope/themes")
        self.assertIn("no themes directory at /nope/themes", text)

    def test_existing_paths_print_no_warning(self):
        text = self._main("--bank", EXAMPLE_BANK, "--themes-dir", EXAMPLES_DIR)
        self.assertNotIn("[warn]", text)
        self.assertIn("Total rows: 3", text)

    def test_config_paths_are_read(self):
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(
                "scan:\n  bank_path: %s\nbrief:\n  themes_dir: %s\n" % (EXAMPLE_BANK, EXAMPLES_DIR)
            )
        self.addCleanup(os.unlink, f.name)
        self.assertIn("Total: 1", self._main("--config", f.name))


class TestBankLines(unittest.TestCase):
    def _bank(self, data):
        import tempfile

        path = os.path.join(tempfile.mkdtemp(), "bank.jsonl")
        with open(path, "wb") as f:
            f.write(data)
        return path

    def _load(self, data):
        import contextlib

        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rows = report.load_bank(self._bank(data))
        return rows, err.getvalue()

    def test_invalid_json_is_skipped_with_a_warning(self):
        rows, err = self._load(b'{"source": "hn"}\nnot json\n{"source": "reddit"}\n')
        self.assertEqual([r["source"] for r in rows], ["hn", "reddit"])
        self.assertIn(":2 skipped, not valid JSON", err)

    def test_a_non_object_line_is_skipped_with_a_warning(self):
        rows, err = self._load(b'[1, 2]\n"text"\n{"source": "hn"}\n')
        self.assertEqual(len(rows), 1)
        self.assertIn(":1 skipped, not a JSON object", err)
        self.assertIn(":2 skipped, not a JSON object", err)

    def test_a_non_utf8_line_is_skipped_with_a_warning(self):
        rows, err = self._load(b'\xff\xfe broken\n{"source": "hn"}\n')
        self.assertEqual(len(rows), 1)
        self.assertIn(":1 skipped, not UTF-8", err)

    def test_a_directory_as_the_bank_is_a_message(self):
        import tempfile

        with self.assertRaises(SystemExit) as ctx:
            report.load_bank(tempfile.mkdtemp())
        self.assertIn("is a directory", str(ctx.exception))


class TestReportConfig(unittest.TestCase):
    def test_a_config_that_is_not_a_mapping_is_a_message(self):
        import subprocess
        import tempfile

        d = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, d, True)
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "report.py")
        for text in ("- a\n- b\n", "", "# only a comment\n"):
            with self.subTest(text=text):
                cfg = os.path.join(d, "c.yaml")
                with open(cfg, "w") as f:
                    f.write(text)
                r = subprocess.run(
                    [sys.executable, script, "--config", cfg], capture_output=True, text=True, cwd=d
                )
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("is empty or not a YAML mapping", r.stderr)
                self.assertNotIn("Traceback", r.stderr)


class TestReportBriefMapping(unittest.TestCase):
    def test_the_coverage_tier_is_read_as_the_writer_reads_it(self):
        import contextlib
        import shutil
        import tempfile

        for tier_lines, tier, warns in (
            ("**Coverage tier:** STRONG", "STRONG", False),
            ("**Coverage tier:** thin", "THIN", False),
            ("**Coverage tier:**   Strong  ", "STRONG", False),
            ("**Coverage tier:** STRONG | THIN", "THIN", True),
            ("**Coverage tier:** STRONG (3 posts)", "THIN", True),
            ("**Coverage tier:**", "THIN", True),
            ("", "THIN", True),
            ("```\n**Coverage tier:** STRONG\n```\n\n**Coverage tier:** THIN", "THIN", False),
            ("<!-- **Coverage tier:** STRONG -->\n**Coverage tier:** THIN", "THIN", False),
        ):
            with self.subTest(tier_lines=tier_lines):
                d = tempfile.mkdtemp()
                self.addCleanup(shutil.rmtree, d, True)
                with open(os.path.join(d, "theme-t.md"), "w", encoding="utf-8") as f:
                    f.write("# Theme: T\n**Status:** draft\n%s\n\n## Signals\n" % tier_lines)
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    themes = report.load_themes(d)
                self.assertEqual(themes[0]["coverage_tier"], tier)
                self.assertEqual("Coverage tier" in err.getvalue(), warns, err.getvalue())

    def test_a_scan_that_is_not_a_mapping_is_a_message(self):
        import shutil
        import subprocess
        import tempfile

        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "report.py")
        for scan in ("[1]", "just text"):
            with self.subTest(scan=scan):
                cfg = os.path.join(d, "c.yaml")
                with open(cfg, "w") as f:
                    f.write("scan: %s\n" % scan)
                r = subprocess.run(
                    [sys.executable, script, "--config", cfg], capture_output=True, text=True, cwd=d
                )
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("`scan` in %s must be a mapping" % cfg, r.stderr)
                self.assertNotIn("Traceback", r.stderr)


class TestReportMappings(unittest.TestCase):
    def test_a_brief_that_is_not_a_mapping_is_a_message(self):
        import shutil
        import subprocess
        import tempfile

        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "report.py")
        for brief in ("[1]", "just text"):
            with self.subTest(brief=brief):
                cfg = os.path.join(d, "c.yaml")
                with open(cfg, "w") as f:
                    f.write("scan: {}\nbrief: %s\n" % brief)
                r = subprocess.run(
                    [sys.executable, script, "--config", cfg], capture_output=True, text=True, cwd=d
                )
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("`brief` in %s must be a mapping" % cfg, r.stderr)
                self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()


class TestReportStatus(unittest.TestCase):
    def _status(self, status_lines):
        import contextlib
        import shutil
        import tempfile

        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        with open(os.path.join(d, "theme-t.md"), "w", encoding="utf-8") as f:
            f.write("# Theme: T\n%s\n**Coverage tier:** THIN\n\n## Signals\n" % status_lines)
        with contextlib.redirect_stderr(io.StringIO()):
            return report.load_themes(d)[0]["status"]

    def test_the_status_is_read_as_the_writer_reads_a_doc(self):
        # Only a bold `**Status:**` line in the header counts, as for the writer.
        for lines, status in (
            ("**Status:** approved", "approved"),
            ("Status: approved", "unknown"),
            ("**Status:** approved (by Jane)", "approved (by jane)"),
            ("\n## Author's take\n**Status:** approved", "unknown"),
            ("**Status:** needs_edit", "needs_edit"),
            ("<!-- **Status:** written -->\n**Status:** proposed", "proposed"),
            ("```\n**Status:** written\n```\n**Status:** proposed", "proposed"),
            ("", "unknown"),
        ):
            with self.subTest(lines=lines):
                self.assertEqual(self._status(lines), status)


class TestReportTierFromTheHeader(unittest.TestCase):
    def test_a_tier_line_inside_a_section_is_not_the_tier(self):
        import contextlib
        import shutil
        import tempfile

        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        with open(os.path.join(d, "theme-2026-10-01-t.md"), "w") as f:
            f.write("# Theme: T\n\n**Status:** approved\n\n## Signals\n**Coverage tier:** STRONG\n")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            themes = report.load_themes(d)
        self.assertEqual(themes[0]["coverage_tier"], "THIN")
        self.assertIn("counted as THIN", err.getvalue())
