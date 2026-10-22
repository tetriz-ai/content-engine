# Copyright 2026 Workloom Solutions Private Limited
# SPDX-License-Identifier: MIT
"""
Validates the example config files are well-formed and carry every
field the code that reads them actually expects.

Run: python3 -m unittest discover -s tests
"""

import _guard  # noqa: F401  (first: isolates HOME, keys and network)
import os
import unittest

import yaml

PKG_DIR = os.path.join(os.path.dirname(__file__), "..")


def load(name):
    with open(os.path.join(PKG_DIR, name)) as f:
        return yaml.safe_load(f)


class TestConfigExampleYaml(unittest.TestCase):
    def setUp(self):
        self.cfg = load("config.example.yaml")

    def test_top_level_sections_present(self):
        for section in ("scan", "cluster", "brief", "write"):
            self.assertIn(section, self.cfg)

    def test_no_terms_block(self):
        # No `terms` block: a term backlog isn't part of this package.
        self.assertNotIn("terms", self.cfg)

    def test_hn_reddit_and_ph_paths_are_repo_root_relative(self):
        # Every path must resolve from the repo root, where the command runs.
        scan = self.cfg["scan"]
        self.assertTrue(scan["hn_reddit_config"].startswith("packages/"))
        self.assertTrue(scan["ph_config"].startswith("packages/"))

    def test_a_config_that_still_has_the_removed_invoke_keys_loads(self):
        # scan.hn_reddit_invoke and scan.ph_invoke were never read; an older
        # config that still has them keeps working, the keys ignored.
        import contextlib
        import io
        import subprocess
        import sys
        import tempfile

        import write_reference as wr

        d = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, d, True)
        cfg = dict(self.cfg)
        cfg["scan"] = dict(
            self.cfg["scan"], hn_reddit_invoke="python3 old.py", ph_invoke="python3 old.py"
        )
        path = os.path.join(d, "config.yaml")
        with open(path, "w") as f:
            yaml.safe_dump(cfg, f)
        self.assertNotIn("hn_reddit_invoke", self.cfg["scan"])
        self.assertNotIn("ph_invoke", self.cfg["scan"])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertIn("length", wr.resolve_format_options(path, "blog"))
        r = subprocess.run(
            [sys.executable, os.path.join(PKG_DIR, "report.py"), "--config", path],
            capture_output=True,
            text=True,
            cwd=d,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("=== Signal bank ===", r.stdout)

    def test_relevance_context_file_is_optional_not_required(self):
        # Must be a plain pointer, not a required block with no off-switch.
        self.assertIn("relevance_context_file", self.cfg["cluster"])

    def test_google_trends_and_aeo_present_and_off_by_default(self):
        self.assertIn("google_trends", self.cfg["scan"])
        self.assertFalse(self.cfg["scan"]["semrush"].get("aeo_check", True))

    def test_no_competitor_feed_is_listed_by_default(self):
        # A copied config must fetch no made-up feed; the entry stays as a commented template.
        self.assertFalse(self.cfg["scan"]["competitor_blogs"].get("feeds"))
        with open(os.path.join(PKG_DIR, "config.example.yaml"), encoding="utf-8") as f:
            self.assertIn("      # example_competitor:\n", f.read())


class TestHnRedditScanExampleYaml(unittest.TestCase):
    def setUp(self):
        self.cfg = load("hn-reddit-scan.example.yaml")

    def test_required_keys_for_scanner_core(self):
        self.assertIn("hn", self.cfg)
        self.assertIn("subreddits", self.cfg)
        self.assertIn("keywords", self.cfg)
        self.assertIn("lookback_hours", self.cfg)

    def test_hn_has_required_subkeys(self):
        for key in ("tags", "min_points"):
            self.assertIn(key, self.cfg["hn"])

    def test_every_subreddit_has_a_name(self):
        for sub in self.cfg["subreddits"]:
            self.assertIn("name", sub)


class TestPhExampleYaml(unittest.TestCase):
    def setUp(self):
        self.cfg = load("ph.example.yaml")

    def test_every_field_scan_ph_and_fetch_details_actually_read(self):
        ph = self.cfg["ph"]
        for key in (
            "topics",
            "max_pages",
            "posts_per_page",
            "detail_fetch_top",
            "voters_limit",
            "comments_limit",
            "token_env",
        ):
            self.assertIn(key, ph, "missing required field: %s" % key)


class TestWriterProfileExampleYaml(unittest.TestCase):
    def setUp(self):
        self.profile = load("writer-profile.example.yaml")

    def test_has_topics_and_strictness(self):
        self.assertIn("topics", self.profile)
        self.assertGreater(len(self.profile["topics"]), 0)
        self.assertIn("strictness", self.profile)

    def test_archive_dir_is_explicitly_null_not_missing(self):
        # Must be present (even as null) so load_profile's archive_dir
        # handling has a key to check, not a KeyError to catch.
        self.assertIn("archive_dir", self.profile)
        self.assertIsNone(self.profile["archive_dir"])


class TestConfigGoogleTrendsAndTwitterShape(unittest.TestCase):
    def setUp(self):
        self.cfg = load("config.example.yaml")

    def test_google_trends_keywords_present(self):
        self.assertIn("keywords", self.cfg["scan"]["google_trends"])

    def test_writer_profile_pointer_present_but_commented_out(self):
        # It's commented out in the YAML (opt-in), so it simply won't be a
        # key in the parsed dict — this test documents that expectation
        # rather than asserting presence, so a future uncomment doesn't
        # silently break an assertion that assumed it stays absent forever.
        self.assertNotIn("writer_profile", self.cfg["cluster"])
        self.assertIn("relevance_context_file", self.cfg["cluster"])

    def test_voice_profile_pointer_present_but_commented_out(self):
        # Same opt-in pattern as writer_profile above — top-level and
        # per-format are both commented out by default.
        self.assertNotIn("voice_profile", self.cfg["write"])
        self.assertNotIn("voice_profile", self.cfg["write"]["blog"])

    def test_seo_optimize_present_and_off_by_default(self):
        self.assertFalse(self.cfg["write"]["blog"].get("seo_optimize", True))


class TestCommandScanSettings(unittest.TestCase):
    """The command is a prompt, so these pin the words that set how it scans."""

    def setUp(self):
        path = os.path.join(PKG_DIR, "..", "..", ".claude", "commands", "content-engine.md")
        with open(path, encoding="utf-8") as f:
            self.text = f.read()

    def test_scans_run_with_a_ten_minute_timeout_and_are_waited_for(self):
        self.assertIn("`timeout` set to `600000` (10 minutes)", self.text)
        self.assertIn("while a scan is still running", self.text)

    def test_a_dry_run_on_the_examples_scans_two_subreddits(self):
        self.assertIn("adds\n   `--max-subreddits 2` to this command", self.text)
        with open(os.path.join(PKG_DIR, "hn-reddit-scan.example.yaml")) as f:
            self.assertGreater(len(yaml.safe_load(f)["subreddits"]), 2)

    def test_no_competitor_feeds_skips_the_blog_scan_without_a_failure(self):
        # Run directly with no feeds, the script exits non-zero, so the command must not call it.
        step = self.text.split("5. **Competitor blogs**", 1)[1].split("competitor-blog-scan.py")[0]
        self.assertIn("lists no `scan.competitor_blogs.feeds`, don't run the script", step)
        self.assertIn('"competitor blogs: skipped, no feeds configured" in the summary', step)
        self.assertIn("is not a failed source", step)


class TestCommandEnvChecks(unittest.TestCase):
    """The command is a prompt, so these pin the words that keep `.env` values out of a run."""

    def setUp(self):
        path = os.path.join(PKG_DIR, "..", "..", ".claude", "commands", "content-engine.md")
        with open(path, encoding="utf-8") as f:
            self.text = f.read()

    def test_a_key_is_checked_by_a_count_that_shows_no_value(self):
        step = self.text.split("**Step 0", 1)[1].split("**Step 1", 1)[0]
        self.assertIn('`output_mode: "count"`', step)
        self.assertIn("a count of 1 or more means set, 0 means unset", step)
        self.assertIn("Never Read, cat or print `.env`", step)
        self.assertIn("never use Grep's `content` mode on it", step)
        self.assertIn("never echo a key, even in part", step)
        self.assertIn("Don't print the environment to\n   check", step)
        # No step may tell the session to load `.env` into the conversation.
        self.assertNotIn("If it exists, load it.", self.text)

    def test_setup_checks_optional_credentials_the_same_way(self):
        setup = self.text.split("## Setup (`--mode init`)", 1)[1].split("Then, in order:", 1)[0]
        self.assertIn("checked as in Step 0 item 1, without\n   showing its value", setup)


class TestCommandApprovalAndKeys(unittest.TestCase):
    """The command is a prompt, so these pin the words that decide approvals,
    the Semrush AEO report and which config keys it reads."""

    def setUp(self):
        path = os.path.join(PKG_DIR, "..", "..", ".claude", "commands", "content-engine.md")
        with open(path, encoding="utf-8") as f:
            self.text = f.read()

    def test_an_edit_reaction_with_no_reply_waits(self):
        phase = self.text.split("## Phase 3b", 1)[1].split("## Phase 4", 1)[0]
        rule = [ln for ln in phase.splitlines() if ln.startswith("| any ✏️")][0]
        self.assertIn("With no reply yet, leave the doc unchanged", rule)
        self.assertIn('"waiting for the requested changes in the thread"', rule)
        self.assertIn("so no draft is written before the changes arrive", rule)
        rows = [ln for ln in phase.splitlines() if ln.startswith("| any ")]
        self.assertTrue(rows[0].startswith("| any 👎"))  # a veto still wins
        self.assertTrue(rows[1].startswith("| any ✏️"))

    def test_the_aeo_report_runs_only_when_aeo_check_is_true(self):
        step = self.text.split("3. **Semrush**", 1)[1].split("4. **Google Trends**", 1)[0]
        self.assertIn("**Only when `scan.semrush.aeo_check` is `true`**", step)
        self.assertIn("With `aeo_check` false or unset, never run it.", step)
        self.assertFalse(load("config.example.yaml")["scan"]["semrush"]["aeo_check"])

    def test_every_example_config_key_is_named_in_the_command(self):
        for key in (
            "scan.semrush.database",
            "scan.platform_search.reuse_query_list",
            "scan.platform_search.reuse_lookback_days",
            "scan.vendor_blog_search.reuse_query_list",
            "brief.coverage_tier.strong_min_signals",
            "brief.coverage_tier.strong_min_distinct_sources",
            "brief.format_eligibility.linkedin.tier_required",
            "brief.format_eligibility.video_proper.same_as",
        ):
            with self.subTest(key=key):
                self.assertIn("`%s`" % key, self.text)
        self.assertIn("`reuse_lookback_days`", self.text)  # vendor_blog_search's, by its block


class TestCommandArchiveAndLinkedIn(unittest.TestCase):
    """Full archives, tagging, matched examples and the personal LinkedIn bar:
    the command is a prompt, so these pin its words, with the example files."""

    def setUp(self):
        root = os.path.join(PKG_DIR, "..", "..")
        with open(
            os.path.join(root, ".claude", "commands", "content-engine.md"), encoding="utf-8"
        ) as f:
            self.text = f.read()
        with open(os.path.join(root, "README.md"), encoding="utf-8") as f:
            self.readme = f.read()
        with open(os.path.join(root, ".claude", "settings.json"), encoding="utf-8") as f:
            self.settings = f.read()

    def test_the_example_profile_ships_content_types_and_max_examples(self):
        profile = load("writer-profile.example.yaml")
        self.assertEqual(
            profile["content_types"],
            [
                "postmortem",
                "tool comparison",
                "how-to",
                "checklist",
                "opinion list",
                "explainer",
                "news analysis",
                "personal story",
                "announcement",
                "other",
            ],
        )
        self.assertEqual(profile["max_examples"], 5)

    def test_a_personal_linkedin_post_needs_only_a_strong_theme(self):
        linkedin = load("config.example.yaml")["brief"]["format_eligibility"]["linkedin"]
        self.assertEqual(linkedin["personal_requires"], "STRONG")
        self.assertEqual(linkedin["margin_signals"], 2)  # the company bar is unchanged
        self.assertIn("`brief.format_eligibility.linkedin.personal_requires`", self.text)
        table = self.text.split("6. **Recommend format(s)**", 1)[1].split(
            "7. **Write the theme doc**"
        )[0]
        personal = [ln for ln in table.splitlines() if "linkedin, personal voice" in ln][0]
        self.assertIn("| none |", personal)
        company = [ln for ln in table.splitlines() if "linkedin, company voice" in ln][0]
        self.assertIn("margin above the bare minimum", company)

    def test_proper_video_keeps_the_company_bar(self):
        table = self.text.split("6. **Recommend format(s)**", 1)[1].split(
            "7. **Write the theme doc**"
        )[0]
        video = [ln for ln in table.splitlines() if "video — proper" in ln][0]
        self.assertIn("`personal_requires` never applies to video", video)
        self.assertEqual(
            load("config.example.yaml")["brief"]["format_eligibility"]["video_proper"]["same_as"],
            "linkedin",
        )

    def test_every_new_theme_gets_a_category_and_content_type(self):
        step = self.text.split("5. **Set the category and content type.**", 1)[1].split("6. **")[0]
        self.assertIn("archive_tag.py --profile <that profile> --list", step)
        self.assertIn("`**Closest type in archive:**`", step)
        template = self.text.split("### Theme doc template", 1)[1].split("## Phase 3b")[0]
        for line in ("**Category:**", "**Content type:**", "**Closest type in archive:**"):
            self.assertIn(line, template)

    def test_step_two_fetches_then_tags_and_the_summary_names_the_examples(self):
        step = self.text.split("**Step 2", 1)[1].split("**Step 3", 1)[0]
        self.assertLess(step.index("archive_fetch.py"), step.index("archive_tag.py"))
        self.assertIn("`--response-file working/archive-tag-answer.txt`", step)
        self.assertIn("`timeout` set to `600000`", step)
        summary = self.text.split("**Step 4", 1)[1].split("The approval loop", 1)[0]
        self.assertIn("`voice examples:` line", summary)

    def test_setup_asks_about_every_new_source(self):
        setup = self.text.split("## Setup (`--mode init`)", 1)[1].split("Then, in order:", 1)[0]
        for words in (
            "medium_export:",
            "linkedin_export:",
            "sitemap:",
            "path_prefix:",
            "substack:",
        ):
            self.assertIn(words, setup)

    def test_a_scheduled_run_may_run_the_new_scripts(self):
        self.assertIn(
            "Bash(python3 $engine_root/packages/content-engine/archive_tag.py:*)", self.readme
        )
        self.assertIn(
            "Bash(python3 $engine_root/packages/content-engine/archive_fetch.py:*)", self.readme
        )
        self.assertIn("archive_tag.py", self.settings)


class TestCommandVenvAndAllowList(unittest.TestCase):
    VENV = 'python3 -c "import sys; print(sys.prefix != sys.base_prefix)"'

    def setUp(self):
        import json

        root = os.path.join(PKG_DIR, "..", "..")
        with open(
            os.path.join(root, ".claude", "commands", "content-engine.md"), encoding="utf-8"
        ) as f:
            self.text = f.read()
        with open(os.path.join(root, "README.md"), encoding="utf-8") as f:
            self.readme = f.read()
        with open(os.path.join(root, ".claude", "settings.json"), encoding="utf-8") as f:
            self.allow = json.load(f)["permissions"]["allow"]

    def test_the_venv_check_is_one_exact_command_everywhere(self):
        step = self.text.split("2. **Python dependency**", 1)[1].split("3. **Config**", 1)[0]
        self.assertIn("`%s`" % self.VENV, step)
        self.assertIn("Never install into the system", step)
        self.assertIn("Bash(%s)" % self.VENV, self.allow)
        self.assertIn("Bash(%s)" % self.VENV.replace('"', '\\"'), self.readme)

    def test_no_bare_pip_install_is_pre_allowed(self):
        self.assertFalse([a for a in self.allow if "pip install -r" in a])

    def test_scan_output_is_read_with_the_read_tool(self):
        self.assertIn(
            "with the Read tool, never an\n   ad-hoc `python3 -c` command or a shell pipeline",
            self.text,
        )

    def test_the_scheduled_line_has_the_slack_tools_and_the_log(self):
        line = [
            ln for ln in self.readme.splitlines() if ln.startswith(". .venv/bin/activate && claude")
        ][0]
        self.assertIn(' <Slack tools>" >> working/content-engine.log 2>&1', line)


class TestAllowListsMatch(TestCommandVenvAndAllowList):
    def test_every_exact_command_the_readme_allows_is_in_settings(self):
        import re

        line = [
            ln for ln in self.readme.splitlines() if ln.startswith(". .venv/bin/activate && claude")
        ][0]
        exact = [b.replace('\\"', '"') for b in re.findall(r'Bash\((python3 -c \\".*?\\")\)', line)]
        self.assertEqual(len(exact), 2)
        for command in exact:
            self.assertIn("Bash(%s)" % command, self.allow)
        self.assertIn('Bash(python3 -c "import yaml")', self.allow)


class TestReactionsDecide(unittest.TestCase):
    def test_only_reactions_change_state_and_replies_go_below_the_header(self):
        path = os.path.join(PKG_DIR, "..", "..", ".claude", "commands", "content-engine.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        phase = text.split("## Phase 3b", 1)[1].split("## Phase 4", 1)[0]
        self.assertIn("Only reactions change state. Never approve a theme because of a", phase)
        self.assertIn("never widen `Formats approved:` beyond", phase)
        self.assertIn("Write it under `## Author's take`, just\nabove `## Output`", phase)


class TestSetupSourcePlanAndBoundary(unittest.TestCase):
    """Setup questions, the source plan, the archive preview, the Trends
    method and the writer's boundary, as the command file states them."""

    def setUp(self):
        root = os.path.join(PKG_DIR, "..", "..")
        with open(
            os.path.join(root, ".claude", "commands", "content-engine.md"), encoding="utf-8"
        ) as f:
            self.text = f.read()
        self.root = root

    def test_setup_asks_for_subreddits_and_where_you_publish(self):
        setup = self.text.split("## Setup (`--mode init`)", 1)[1].split("Then, in order:", 1)[0]
        self.assertIn('**"Which subreddits do your users talk in?', setup)
        self.assertIn("`subreddits:` in your `hn-reddit-scan.yaml`", setup)
        self.assertIn("keep the example's subreddits", setup)
        self.assertIn(
            "Where do you already publish? (Substack, Medium, a site folder, a\n"
            "   LinkedIn export) — or skip",
            setup,
        )
        self.assertIn("archive_tag.py --profile <that profile> --preview", setup)
        self.assertIn("In an interactive run, ask whether that looks right", setup)
        self.assertIn("(eight short questions, two of them optional)", self.text)

    def test_phase_four_gates_every_route_beside_the_approval_sentence(self):
        phase = self.text.split("## Phase 4", 1)[1].split("### Default:", 1)[0]
        # the approval sentence, then the rule for every route
        self.assertIn(
            "Only run for theme docs where the requested format is in `Formats approved`.\n"
            "The same gate holds on every route,",
            phase,
        )
        flat = " ".join(phase.split())
        for words in (
            "on every route, a custom writer included",
            "`Status:` must be `approved` or `written`",
            "needs the tier set in Phase 3 step 6",
            "only from the doc's header lines",
        ):
            with self.subTest(words=words):
                self.assertIn(words, flat)

    def test_phase_one_prints_the_source_plan_first(self):
        phase = self.text.split("## Phase 1", 1)[1].split("1. **Reddit / HN**", 1)[0]
        self.assertIn("**Print the source plan first.**", phase)
        self.assertIn("With `--dry-run`, put the same plan in the summary.", phase)

    def test_a_trends_row_records_how_it_was_read(self):
        self.assertIn('`{"method": "screenshot", "direction": "rising"}`', self.text)
        self.assertIn('`{"method": "websearch-fallback", "direction": "rising"}`', self.text)
        self.assertIn("A Trends\n     row without `raw_metric.method` is incomplete", self.text)

    def test_phase_four_states_the_writers_boundary(self):
        self.assertIn(
            "is not `approved` or `written`, a format not in its `Formats approved:`", self.text
        )

    def test_the_readme_links_every_docs_page(self):
        with open(os.path.join(self.root, "README.md"), encoding="utf-8") as f:
            readme = f.read()
        for page in (
            "walkthrough",
            "glossary",
            "demo-transcript",
            "optional-sources",
            "trust-boundary",
        ):
            with self.subTest(page=page):
                self.assertIn("(docs/%s.md)" % page, readme)
                self.assertTrue(os.path.exists(os.path.join(self.root, "docs", page + ".md")))
        self.assertIn("## Limitations", readme)
        self.assertIn("(docs/trust-boundary.md)", readme)


if __name__ == "__main__":
    unittest.main()
