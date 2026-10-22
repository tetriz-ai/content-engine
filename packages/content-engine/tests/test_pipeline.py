# Copyright 2026 Workloom Solutions Private Limited
# SPDX-License-Identifier: MIT
import _guard  # noqa: F401
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]


class TestPipeline(unittest.TestCase):
    def test_imported_helpers_read_only_the_callers_credential_file(self):
        with tempfile.TemporaryDirectory() as directory:
            env = Path(directory) / "packages/content-engine/.env"
            env.parent.mkdir(parents=True)
            env.write_text("ANTHROPIC_API_KEY=fixture-not-a-real-key\n")
            code = (
                "import sys;sys.path.insert(0,sys.argv[1]);"
                "import write_reference,relevance_scorer,archive_tag;"
                "assert all(m.get_api_key()=='fixture-not-a-real-key' "
                "for m in (write_reference,relevance_scorer,archive_tag))"
            )
            run = subprocess.run(
                [sys.executable, "-c", code, str(ROOT / "packages/content-engine")],
                cwd=directory,
                capture_output=True,
                text=True,
            )
            self.assertEqual(run.returncode, 0, run.stderr)

    def test_installs_all_three_skills_on_both_hosts_without_creating_state(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for _ in range(2):
                subprocess.run(
                    [sys.executable, str(ROOT / "scripts/install-skills.py"), "--into", directory],
                    check=True,
                    capture_output=True,
                )
            manifest = json.loads((ROOT / "pipeline-manifest.json").read_text())
            for host in (".agents", ".claude"):
                for name, path in manifest["skills"].items():
                    link = target / host / "skills" / name
                    self.assertTrue(link.is_symlink())
                    self.assertEqual(link.resolve(), (ROOT / path).resolve())
            self.assertFalse((target / "working").exists())
            self.assertFalse((target / "packages").exists())

    def test_collision_is_preflighted_before_any_link_is_written(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            collision = target / ".claude/skills/editorial-draft"
            collision.mkdir(parents=True)
            (collision / "notes").write_text("my edits")
            run = subprocess.run(
                [sys.executable, str(ROOT / "scripts/install-skills.py"), "--into", directory],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(run.returncode, 0)
            self.assertEqual((collision / "notes").read_text(), "my edits")
            self.assertFalse((target / ".agents/skills/content-engine").exists())

    def test_resolver_keeps_config_and_state_in_caller_not_imported_engine(self):
        with tempfile.TemporaryDirectory() as directory:
            run = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/resolve-context.py"),
                    "--working-root",
                    directory,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            context = json.loads(run.stdout)
            self.assertEqual(context["engine_root"], str(ROOT))
            self.assertTrue(
                context["config_path"].startswith(str(Path(directory).resolve()) + os.sep)
            )
            self.assertTrue(
                context["working_dir"].startswith(str(Path(directory).resolve()) + os.sep)
            )
            self.assertFalse(Path(context["config_path"]).exists())

    def test_default_writer_is_full_pipeline_and_reference_is_explicit(self):
        import yaml

        config = yaml.safe_load((ROOT / "packages/content-engine/config.example.yaml").read_text())
        self.assertNotIn("command", config["write"]["blog"])
        manifest = json.loads((ROOT / "pipeline-manifest.json").read_text())
        self.assertEqual(manifest["writing"]["blog"], ["blog", "editorial-draft"])
        self.assertEqual(manifest["writing"]["linkedin"], ["editorial-draft"])
        for route in manifest["writing"].values():
            for skill in route:
                self.assertIn(skill, manifest["skills"])
        self.assertEqual(manifest["output_kinds"]["video"], "brief")

    def test_every_declared_resource_exists_and_lower_layers_do_not_depend_on_caller(self):
        manifest = json.loads((ROOT / "pipeline-manifest.json").read_text())
        for resource in manifest["required_files"]:
            self.assertTrue((ROOT / resource).is_file(), resource)
        for folder in (ROOT / "skills", ROOT / "references"):
            for file in folder.rglob("*.md"):
                text = file.read_text()
                for forbidden in (
                    "caller-specific-command",
                    ".caller-install.json",
                    "caller/runtime/payload",
                    "<caller_brain_dir>",
                ):
                    self.assertNotIn(forbidden, text, str(file))


class TestCanonicalWritingRoutes(unittest.TestCase):
    def test_per_format_routes_preserve_full_defaults_and_explicit_overrides(self):
        command = (ROOT / ".claude/commands/content-engine.md").read_text()
        notes = command.split("### Per-format notes\n", 1)[1].split("\n---", 1)[0]
        blog = notes.split("**`--format blog`**", 1)[1].split("**`--format linkedin`**", 1)[0]
        linkedin = notes.split("**`--format linkedin`**", 1)[1].split("**`--format video", 1)[0]
        self.assertIn("skills/blog/SKILL.md", blog)
        self.assertIn("Editorial Draft", blog)
        self.assertIn("explicit", blog)
        self.assertIn("write.blog.command", blog)
        self.assertEqual(
            " ".join(blog.strip().rstrip("-").split()),
            "— by default, invoke `skills/blog/SKILL.md` and its full Blog → Editorial Draft "
            "workflow as described above. Only an explicit `write.blog.command` in "
            "`config.yaml` selects a custom/reference writer. Blog is the only format "
            "the SEO/AEO pass above applies to. Pass `write.blog.length` to the selected "
            "workflow or adapter prompt.",
        )
        self.assertIn("skills/editorial-draft/SKILL.md", linkedin)
        self.assertIn("explicit", linkedin)
        self.assertIn("write.linkedin.command", linkedin)
        self.assertNotIn("defaults to `write_reference.py`", command)
        self.assertIn("Only an explicitly configured `write.<format>.command`", command)

    def test_phase_four_requires_requested_format_approval(self):
        command = (ROOT / ".claude/commands/content-engine.md").read_text()
        phase = command.split("## Phase 4 — Write", 1)[1]
        self.assertIn(
            "Only run for theme docs where the requested format is in `Formats approved`.",
            phase,
        )

    def test_phase_four_preview_reports_route_without_drafting(self):
        command = (ROOT / ".claude/commands/content-engine.md").read_text()
        phase = command.split("## Phase 4 — Write", 1)[1]
        self.assertIn(
            "With `--dry-run`, report this route and intended paths without drafting or applying.",
            phase,
        )

    def test_readme_custom_writer_replaces_bundled_per_format_workflow(self):
        readme = (ROOT / "README.md").read_text()
        custom = readme.split("### Plug in a writer of your own", 1)[1].split("\n### ", 1)[0]
        self.assertIn(
            "Point `write.<format>.command` in `config.yaml` at a program like it, "
            "and the run calls it in place of the bundled per-format workflow.",
            custom,
        )
        self.assertNotIn("in place of `write_reference.py`", custom)


class TestOperationalContract(unittest.TestCase):
    def test_product_bench_import_keeps_extension_notices_with_the_linked_pipeline(self):
        with tempfile.TemporaryDirectory(prefix="importing-caller-") as directory:
            caller = Path(directory)
            subprocess.run(
                [sys.executable, str(ROOT / "scripts/install-skills.py"), "--into", directory],
                check=True,
                capture_output=True,
            )
            for host in (".agents", ".claude"):
                engine = (caller / host / "skills/content-engine").resolve()
                notices = (engine / "THIRD-PARTY-NOTICES.md").read_text()
                self.assertIn("Apache-2.0", notices)
                self.assertIn("CORE-EEAT", notices)
                self.assertTrue((engine / "third_party/licenses/seo-geo-Apache-2.0.txt").is_file())
                for name in ("blog", "editorial-draft"):
                    self.assertEqual(
                        (caller / host / "skills" / name).resolve(), engine / "skills" / name
                    )
            self.assertFalse((caller / "working").exists())

    def test_contributor_rules_allow_explicit_live_and_scheduled_runs(self):
        guide = (ROOT / "CLAUDE.md").read_text()
        self.assertNotIn("Do not run `/content-engine` without `--dry-run` here", guide)
        self.assertIn("An explicitly authorized live or scheduled run may execute", guide)

    def test_scheduled_allowlist_covers_resolver_and_date_fetches_for_imported_engines(self):
        readme = (ROOT / "README.md").read_text()
        line = next(
            ln for ln in readme.splitlines() if ln.startswith(". .venv/bin/activate && claude")
        )
        self.assertIn("WebFetch", line)
        self.assertIn("Bash(python3 $engine_root/scripts/resolve-context.py:*)", line)
        self.assertIn("Bash(python3 $engine_root/packages/scanner-core/scanner_core.py:*)", line)
        self.assertNotIn("Bash(python3 packages/", line)


class TestEditorialRename(unittest.TestCase):
    def test_old_host_links_resolve_without_replacing_local_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            legacy = target / ".agents/skills/articleforge"
            legacy.parent.mkdir(parents=True)
            legacy.symlink_to(ROOT / "skills/articleforge", target_is_directory=True)
            custom = target / ".claude/skills/articleforge"
            custom.mkdir(parents=True)
            (custom / "SKILL.md").write_text("local edits")
            run = subprocess.run(
                [sys.executable, str(ROOT / "scripts/install-skills.py"), "--into", directory],
                capture_output=True,
                text=True,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            for host in (".agents", ".claude"):
                self.assertEqual(
                    (target / host / "skills/editorial-draft").resolve(),
                    (ROOT / "skills/editorial-draft").resolve(),
                )
            self.assertEqual(legacy.resolve(), (ROOT / "skills/editorial-draft").resolve())
            self.assertEqual((custom / "SKILL.md").read_text(), "local edits")

    def test_resolver_retains_the_deprecated_resource_key(self):
        run = subprocess.run(
            [sys.executable, str(ROOT / "scripts/resolve-context.py")],
            capture_output=True,
            text=True,
            check=True,
        )
        context = json.loads(run.stdout)
        self.assertEqual(context["articleforge"], context["editorial-draft"])
        self.assertTrue(Path(context["editorial-draft"]).is_file())
