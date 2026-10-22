# Copyright 2026 Workloom Solutions Private Limited
# SPDX-License-Identifier: MIT
"""
Unit tests for archive_fetch.py. Feeds are local files read through file://
URLs, so no test reaches the network.

Run: python3 -m unittest discover -s tests
"""

import _guard  # noqa: F401  (first: isolates HOME, keys and network)
import contextlib
import gzip
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import zipfile
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import archive_fetch as af

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "archive_fetch.py")

LONG_PARAGRAPH = "This is a sentence from a long Medium article. " * 40  # ~1,900 chars


def saved(archive_dir):
    """The post files in archive_dir, without the tag index."""
    return sorted(n for n in os.listdir(archive_dir) if not n.startswith("."))


def rss(*items):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">'
        "<channel><title>My blog</title>%s</channel></rss>" % "".join(items)
    )


def rss_item(title, link, date, html, description=None):
    return (
        "<item><title>%s</title><link>%s</link><pubDate>%s</pubDate>"
        "<description><![CDATA[%s]]></description>"
        "<content:encoded><![CDATA[%s]]></content:encoded></item>"
        % (title, link, date, description or "short teaser", html)
    )


ATOM_FEED = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<feed xmlns="http://www.w3.org/2005/Atom"><title>Blog</title>'
    "<entry><title>An Atom post</title>"
    '<link rel="alternate" href="https://blog.example.com/atom-post"/>'
    "<published>2026-09-01T10:00:00Z</published>"
    '<content type="html">&lt;p&gt;Atom body text.&lt;/p&gt;</content></entry></feed>'
)


class TestFeedUrl(unittest.TestCase):
    def test_medium_user_and_publication(self):
        self.assertEqual(
            af.feed_url({"medium": "@example-author"}), "https://medium.com/feed/@example-author"
        )
        self.assertEqual(
            af.feed_url({"medium": "example-author"}), "https://medium.com/feed/example-author"
        )
        self.assertEqual(
            af.feed_url({"medium": "https://medium.com/@example-author/"}),
            "https://medium.com/feed/@example-author",
        )

    def test_substack_name_and_custom_domain(self):
        self.assertEqual(
            af.feed_url({"substack": "example-author"}), "https://example-author.substack.com/feed"
        )
        self.assertEqual(
            af.feed_url({"substack": "https://news.example.com/"}), "https://news.example.com/feed"
        )
        self.assertEqual(
            af.feed_url({"substack": "news.example.com"}), "https://news.example.com/feed"
        )

    def test_a_medium_address_without_its_scheme(self):
        self.assertEqual(
            af.feed_url({"medium": "medium.com/@example-author"}),
            "https://medium.com/feed/@example-author",
        )
        self.assertEqual(
            af.feed_url({"medium": "example-author.medium.com"}),
            "https://example-author.medium.com/feed",
        )

    def test_the_user_agent_is_the_bot_form_medium_accepts(self):
        # Medium resets the connection unless the User-Agent starts with
        # Mozilla/5.0; the compatible form still names this tool.
        self.assertEqual(
            af.UA,
            "Mozilla/5.0 (compatible; content-engine; +https://github.com/tetriz-ai/content-engine)",
        )

    def test_rss_is_used_as_given(self):
        self.assertEqual(
            af.feed_url({"rss": "https://example-author.example.com/feed.xml"}),
            "https://example-author.example.com/feed.xml",
        )

    def test_bad_sources_are_a_message(self):
        for bad in (
            {"medium": ""},
            {"tumblr": "example-author"},
            {"rss": "ftp://example-author.example.com/feed"},
            {"rss": "example-author.example.com/feed"},
            {"medium": "@a", "rss": "https://b.example.com/feed"},
            "medium: example-author",
        ):
            with self.subTest(source=bad):
                with self.assertRaises(ValueError):
                    af.feed_url(bad)


class TestFeedAddresses(unittest.TestCase):
    def test_www_medium_com_is_medium_com(self):
        for value in ("www.medium.com/@example-author", "https://www.medium.com/@example-author"):
            with self.subTest(value=value):
                self.assertEqual(
                    af.feed_url({"medium": value}), "https://medium.com/feed/@example-author"
                )

    def test_a_substack_com_profile_is_the_publication_feed(self):
        for value in ("substack.com/@example-author", "https://substack.com/@example-author"):
            with self.subTest(value=value):
                self.assertEqual(
                    af.feed_url({"substack": value}), "https://example-author.substack.com/feed"
                )
        with self.assertRaises(ValueError):
            af.feed_url({"substack": "https://substack.com/"})

    def test_a_slug_keeps_accented_and_non_latin_letters(self):
        self.assertEqual(af._slug("Ünïcödé Title"), "unicode-title")
        self.assertEqual(af._slug("テスト 記事"), "テスト-記事")
        self.assertEqual(af._slug("!!!"), "post")

    def test_an_atom_link_with_no_rel_is_the_post_link(self):
        feed = (
            '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">'
            '<entry><title>X</title><link href="https://blog.example.com/x"/>'
            "<published>2026-09-01T00:00:00Z</published><content>Body.</content></entry></feed>"
        )
        self.assertEqual(af.parse_feed(feed.encode())[0]["url"], "https://blog.example.com/x")


class TestSlugsAndSubstackHandles(unittest.TestCase):
    def test_a_slug_keeps_japanese_voicing_and_devanagari_marks(self):
        self.assertEqual(af._slug("デザイン"), "デザイン")
        self.assertEqual(af._slug("हिन्दी"), "हिन्दी")
        self.assertEqual(af._slug("Ça va, Ελλάδα"), "ca-va-ελλαδα")

    def test_a_slug_keeps_korean_syllables_and_arabic_words(self):
        self.assertEqual(af._slug("한국어"), "한국어")
        self.assertEqual(len(af._slug("한국어")), 3)  # composed again, not jamo
        self.assertEqual(af._slug("مرحبا بالعالم"), "مرحبا-بالعالم")

    def test_www_substack_com_profile(self):
        self.assertEqual(
            af.feed_url({"substack": "www.substack.com/@example-author"}),
            "https://example-author.substack.com/feed",
        )

    def test_a_substack_handle_with_an_at_sign(self):
        self.assertEqual(
            af.feed_url({"substack": "@example-author"}), "https://example-author.substack.com/feed"
        )

    def test_sources_that_name_no_profile_or_publication_are_errors(self):
        for source, needle in (
            ({"medium": "https://medium.com/"}, "names no Medium profile"),
            ({"medium": "https://blog.example.com/"}, "use rss: for a custom domain"),
            ({"medium": "blog.example.com"}, "names no Medium profile"),
            ({"substack": "substack.com/profile/12-example-author"}, "use the publication name"),
            ({"substack": "@"}, "names no publication"),
        ):
            with self.subTest(source=source):
                with self.assertRaises(ValueError) as ctx:
                    af.feed_url(source)
                self.assertIn(needle, str(ctx.exception))


class TestMediumFeedUrls(unittest.TestCase):
    def test_a_medium_feed_url_is_its_own_feed(self):
        for value in ("https://medium.com/feed/@example-author", "medium.com/feed/@example-author"):
            with self.subTest(value=value):
                self.assertEqual(
                    af.feed_url({"medium": value}), "https://medium.com/feed/@example-author"
                )

    def test_a_medium_post_tag_or_app_url_names_no_profile(self):
        for value in (
            "https://medium.com/p/abc123",
            "https://medium.com/tag/ci",
            "https://medium.com/m/signin",
            "https://medium.com/feed/",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError) as ctx:
                    af.feed_url({"medium": value})
                self.assertIn("names no Medium profile", str(ctx.exception))


class TestHtmlToText(unittest.TestCase):
    def test_keeps_paragraphs_headings_and_list_items(self):
        text = af.html_to_text(
            "<h2>Why it matters</h2><p>First <b>bold</b> point.</p>"
            "<ul><li>one</li><li>two</li></ul><p>Last&nbsp;one &amp; done.</p>"
            "<script>alert(1)</script><style>p{}</style>"
        )
        self.assertEqual(
            text, "## Why it matters\n\nFirst bold point.\n\n- one\n- two\n\nLast one & done."
        )

    def test_figure_captions_are_dropped(self):
        text = af.html_to_text(
            "<p>Body.</p><figure><img/><figcaption>Photo by X</figcaption></figure>"
        )
        self.assertEqual(text, "Body.")


class TestParseFeed(unittest.TestCase):
    def test_rss_prefers_the_full_content_over_the_description(self):
        posts = af.parse_feed(
            rss(
                rss_item(
                    "A long post",
                    "https://medium.com/@example-author/a-long-post-123?source=rss",
                    "Tue, 29 Sep 2026 08:00:00 GMT",
                    "<p>%s</p><p>%s</p>" % (LONG_PARAGRAPH, LONG_PARAGRAPH),
                )
            ).encode()
        )
        self.assertEqual(len(posts), 1)
        post = posts[0]
        self.assertEqual(post["title"], "A long post")
        self.assertEqual(
            post["url"], "https://medium.com/@example-author/a-long-post-123?source=rss"
        )
        self.assertEqual(post["published"], "2026-09-29")
        self.assertNotIn("short teaser", post["text"])
        self.assertGreater(len(post["text"]), 3000)

    def test_atom_entries(self):
        posts = af.parse_feed(ATOM_FEED.encode())
        self.assertEqual(
            posts,
            [
                {
                    "title": "An Atom post",
                    "url": "https://blog.example.com/atom-post",
                    "published": "2026-09-01",
                    "text": "Atom body text.",
                    "full": True,
                }
            ],
        )

    def test_atom_xhtml_content_keeps_its_paragraphs(self):
        feed = (
            '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">'
            "<entry><title>X</title>"
            '<content type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml">'
            "<h2>Why</h2><p>One.</p><ul><li>a</li><li>b</li></ul><p>Two.</p></div></content>"
            "</entry></feed>"
        )
        self.assertEqual(
            af.parse_feed(feed.encode())[0]["text"], "## Why\n\nOne.\n\n- a\n- b\n\nTwo."
        )

    def test_a_html_page_is_not_a_feed(self):
        with self.assertRaises(ValueError):
            af.parse_feed(b"<!doctype html><html><body>Just a moment...</body></html>")


class TestRun(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.archive = os.path.join(self.dir, "archive")

    def _feed_file(self, name, content):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return "file://" + path

    def _profile(self, *feed_urls, archive_dir=None, extra=""):
        path = os.path.join(self.dir, "profile.yaml")
        with open(path, "w") as f:
            f.write("archive_dir: %s\narchive_sources:\n" % (archive_dir or self.archive))
            for url in feed_urls:
                f.write("  - rss: %s\n" % url)
            f.write(extra)
        return path

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, SCRIPT, *args], capture_output=True, text=True, cwd=self.dir
        )

    def test_writes_each_post_whole_as_a_markdown_file(self):
        url = self._feed_file(
            "feed.xml",
            rss(
                rss_item(
                    "Why we stopped re-running CI",
                    "https://example-author.example.com/ci",
                    "Tue, 29 Sep 2026 08:00:00 GMT",
                    "<p>%s</p>" % (LONG_PARAGRAPH * 4),
                )
            ),
        )
        r = self._run("--profile", self._profile(url))
        self.assertEqual(r.returncode, 0, r.stderr)
        files = saved(self.archive)
        self.assertEqual(files, ["2026-09-29-why-we-stopped-re-running-ci.md"])
        with open(os.path.join(self.archive, files[0]), encoding="utf-8") as f:
            body = f.read()
        self.assertTrue(body.startswith("# Why we stopped re-running CI\n"))
        self.assertIn("https://example-author.example.com/ci", body)
        self.assertGreater(len(body), 7000)  # the whole article, not an excerpt
        self.assertIn("1 new", r.stdout)

    def test_a_second_run_skips_posts_already_saved_unless_refreshed(self):
        url = self._feed_file(
            "feed.xml",
            rss(
                rss_item(
                    "Post", "https://example-author.example.com/p", "Tue, 29 Sep 2026", "<p>v1</p>"
                )
            ),
        )
        profile = self._profile(url)
        self._run("--profile", profile)
        target = os.path.join(self.archive, "2026-09-29-post.md")
        with open(target, "a") as f:
            f.write("\nmy hand edit\n")
        r = self._run("--profile", profile)
        self.assertIn("1 already saved", r.stdout)
        with open(target) as f:
            self.assertIn("my hand edit", f.read())
        self._run("--profile", profile, "--refresh")
        with open(target) as f:
            self.assertNotIn("my hand edit", f.read())

    def test_dry_run_writes_nothing(self):
        url = self._feed_file(
            "feed.xml",
            rss(
                rss_item(
                    "Post", "https://example-author.example.com/p", "Tue, 29 Sep 2026", "<p>x</p>"
                )
            ),
        )
        r = self._run("--profile", self._profile(url), "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(self.archive))
        self.assertIn("2026-09-29-post.md", r.stdout)

    def test_a_full_post_under_500_characters_is_flagged_and_500_is_not(self):
        url = self._feed_file(
            "feed.xml",
            rss(
                rss_item("Short", "https://blog.example.com/s", "Tue, 29 Sep 2026", "x" * 499),
                rss_item("Exact", "https://blog.example.com/e", "Tue, 29 Sep 2026", "y" * 500),
            ),
        )
        out = self._run("--profile", self._profile(url)).stdout
        self.assertIn("2026-09-29-short.md has 499 characters", out)
        self.assertNotIn("2026-09-29-exact.md has", out)

    def test_a_short_body_is_flagged_as_a_possible_preview(self):
        url = self._feed_file(
            "feed.xml",
            rss(
                rss_item(
                    "Paid post",
                    "https://example-author.example.com/paid",
                    "Tue, 29 Sep 2026",
                    "<p>Teaser.</p>",
                )
            ),
        )
        r = self._run("--profile", self._profile(url))
        self.assertIn("preview", r.stdout + r.stderr)

    def test_a_feed_of_summaries_is_flagged_and_a_short_full_post_is_not(self):
        summary_only = (
            "<item><title>Summary only</title><link>https://example-author.example.com/s</link>"
            "<pubDate>Tue, 29 Sep 2026</pubDate><description>%s</description></item>"
            % ("A long summary. " * 50)
        )
        short_full = rss_item(
            "Short but whole",
            "https://example-author.example.com/w",
            "Tue, 29 Sep 2026",
            "<p>%s</p>" % ("x" * 600),
        )
        url = self._feed_file("feed.xml", rss(summary_only, short_full))
        r = self._run("--profile", self._profile(url))
        out = r.stdout + r.stderr
        self.assertIn("2026-09-29-summary-only.md", out)
        self.assertIn("only a summary", out)
        self.assertNotIn("short-but-whole.md has", out)

    def test_one_broken_source_does_not_stop_the_others(self):
        good = self._feed_file(
            "good.xml",
            rss(
                rss_item(
                    "Good", "https://example-author.example.com/g", "Tue, 29 Sep 2026", "<p>ok</p>"
                )
            ),
        )
        bad = self._feed_file("bad.xml", "<html><body>blocked</body></html>")
        r = self._run("--profile", self._profile(bad, good))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(saved(self.archive), ["2026-09-29-good.md"])
        self.assertIn("failed", r.stderr)

    def test_every_source_failing_exits_non_zero(self):
        bad = self._feed_file("bad.xml", "not a feed")
        r = self._run("--profile", self._profile(bad))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("failed", r.stderr)

    def test_same_title_and_date_from_two_posts_get_two_files(self):
        url = self._feed_file(
            "feed.xml",
            rss(
                rss_item(
                    "Notes", "https://example-author.example.com/a", "Tue, 29 Sep 2026", "<p>a</p>"
                ),
                rss_item(
                    "Notes", "https://example-author.example.com/b", "Tue, 29 Sep 2026", "<p>b</p>"
                ),
            ),
        )
        self._run("--profile", self._profile(url))
        self.assertEqual(saved(self.archive), ["2026-09-29-notes-2.md", "2026-09-29-notes.md"])

    def test_config_errors_are_messages(self):
        cases = {
            "archive_sources:\n  - rss: https://example-author.example.com/feed\n": "archive_dir",
            "archive_dir: x\n": "archive_sources",
            "archive_dir: x\narchive_sources:\n  - tumblr: example-author\n": "tumblr",
            "- just a list\n": "mapping",
        }
        for text, needle in cases.items():
            with self.subTest(needle=needle):
                path = os.path.join(self.dir, "p.yaml")
                with open(path, "w") as f:
                    f.write(text)
                r = self._run("--profile", path)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn(needle, r.stderr)
                self.assertNotIn("Traceback", r.stderr)

    def test_the_fetched_archive_is_what_the_writer_reads(self):
        url = self._feed_file(
            "feed.xml",
            rss(
                rss_item(
                    "Long",
                    "https://example-author.example.com/l",
                    "Tue, 29 Sep 2026",
                    "<p>%s</p>" % LONG_PARAGRAPH,
                )
            ),
        )
        profile = self._profile(url)
        self._run("--profile", profile)
        import write_reference as wr

        cwd = os.getcwd()
        os.chdir(self.dir)
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                excerpts = wr.load_voice_examples(profile)
        finally:
            os.chdir(cwd)
        self.assertEqual(len(excerpts), 1)
        self.assertIn(LONG_PARAGRAPH.strip(), excerpts[0])


# --- full archives and the tag index ------------------------------------------


class FakeWeb:
    """A fake `fetch`: each URL maps to bytes, or to an exception to raise.
    Records every URL asked for."""

    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def __call__(self, url, timeout=20):
        self.calls.append(url)
        page = self.pages.get(url)
        if page is None:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        if isinstance(page, Exception):
            raise page
        return page.encode("utf-8") if isinstance(page, str) else page


class InProcess(unittest.TestCase):
    """Runs archive_fetch.main() in this process with a fake web."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.archive = os.path.join(self.dir, "archive")

    def profile(self, sources_yaml, extra=""):
        path = os.path.join(self.dir, "profile.yaml")
        with open(path, "w", encoding="utf-8") as f:
            f.write("archive_dir: %s\narchive_sources:\n%s%s" % (self.archive, sources_yaml, extra))
        return path

    def run_main(self, web, profile, *args):
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with (
            mock.patch.object(af, "fetch", web),
            mock.patch.object(sys, "argv", ["archive_fetch.py", "--profile", profile, *args]),
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
        ):
            try:
                af.main()
            except SystemExit as e:
                code = e.code if isinstance(e.code, int) else 1
                if isinstance(e.code, str):
                    err.write(e.code)
        return code, out.getvalue(), err.getvalue()

    def read(self, name):
        with open(os.path.join(self.archive, name), encoding="utf-8") as f:
            return f.read()

    def index(self):
        with open(os.path.join(self.archive, ".tags.json"), encoding="utf-8") as f:
            return json.load(f)["posts"]


class TestSourceEntries(unittest.TestCase):
    def test_a_sitemap_needs_a_path_prefix(self):
        for entry in (
            {"sitemap": "https://blog.example.com/sitemap.xml"},
            {"sitemap": "https://blog.example.com/sitemap.xml", "path_prefix": "/"},
            {"sitemap": "https://blog.example.com/sitemap.xml", "path_prefix": 7},
        ):
            with self.subTest(entry=entry):
                with self.assertRaises(ValueError) as ctx:
                    af.parse_source(entry)
                self.assertIn("path_prefix", str(ctx.exception))

    def test_the_prefix_is_normalised_and_settings_are_kept(self):
        kind, value, options = af.parse_source(
            {
                "sitemap": "https://blog.example.com/sitemap.xml",
                "path_prefix": "guides",
                "max_pages": 10,
                "min_gap_seconds": 0.5,
            }
        )
        self.assertEqual((kind, options["path_prefix"]), ("sitemap", "/guides/"))
        self.assertEqual((options["max_pages"], options["min_gap_seconds"]), (10, 0.5))

    def test_settings_a_type_does_not_take_and_bad_values_are_errors(self):
        for entry, needle in (
            ({"rss": "https://blog.example.com/feed", "path_prefix": "/x/"}, "path_prefix"),
            ({"medium_export": "/tmp/x.zip", "min_gap_seconds": 1}, "min_gap_seconds"),
            ({"substack": "example-author", "min_gap_seconds": -1}, "min_gap_seconds"),
            ({"substack": "example-author", "min_gap_seconds": True}, "min_gap_seconds"),
            (
                {"sitemap": "https://b.example.com/s.xml", "path_prefix": "/g/", "max_pages": 0},
                "max_pages",
            ),
            ({"sitemap": "blog.example.com/s.xml", "path_prefix": "/g/"}, "URL"),
            ({"linkedin_export": ""}, "no value"),
            ({"substack": "@"}, "names no publication"),
        ):
            with self.subTest(entry=entry):
                with self.assertRaises(ValueError) as ctx:
                    af.parse_source(entry)
                self.assertIn(needle, str(ctx.exception))

    def test_the_new_types_have_no_feed(self):
        with self.assertRaises(ValueError):
            af.feed_url({"linkedin_export": "/tmp/export.zip"})

    def test_an_explicit_http_substack_domain_keeps_its_scheme(self):
        self.assertEqual(af.substack_base("http://127.0.0.1:8000"), "http://127.0.0.1:8000")
        self.assertEqual(af.substack_base("news.example.com"), "https://news.example.com")


class TestCategory(unittest.TestCase):
    def test_the_deepest_folder_below_the_prefix(self):
        cases = {
            "https://blog.example.com/guides/ci-reliability/flaky-quarantine": "ci-reliability",
            "https://blog.example.com/guides/eng/ci-reliability/flaky-quarantine": "ci-reliability",
            "https://blog.example.com/guides/Test-Tooling/a-guide/": "test-tooling",
            "https://blog.example.com/guides/some-guide": None,
            "https://blog.example.com/blog/ci-reliability/flaky-quarantine": None,
            "": None,
        }
        for url, want in cases.items():
            with self.subTest(url=url):
                self.assertEqual(af.category_from_url(url, "/guides/"), want)

    def test_no_prefix_no_category(self):
        self.assertIsNone(af.category_from_url("https://example-author.substack.com/p/x", None))


def archive_page(*posts):
    return json.dumps(
        [
            {
                "slug": slug,
                "title": title,
                "post_date": date + "T08:00:00.000Z",
                "audience": audience,
                "canonical_url": "https://news.example.com/p/" + slug,
                "type": kind,
            }
            for slug, title, date, audience, kind in posts
        ]
    )


def substack_post(slug, title, date, body, audience="everyone"):
    return json.dumps(
        {
            "slug": slug,
            "title": title,
            "post_date": date + "T08:00:00.000Z",
            "audience": audience,
            "canonical_url": "https://news.example.com/p/" + slug,
            "body_html": body,
        }
    )


SUB = "https://news.example.com/api/v1/"


class TestSubstackArchive(InProcess):
    def web(self, **extra):
        pages = {
            SUB + "archive?sort=new&offset=0&limit=50": archive_page(
                ("second", "Second post", "2026-09-20", "everyone", "newsletter"),
                ("paid-one", "Paid one", "2026-09-10", "only_paid", "newsletter"),
            ),
            SUB + "archive?sort=new&offset=2&limit=50": archive_page(
                ("first", "First post", "2026-01-05", "everyone", "newsletter"),
                ("a-thread", "Open thread", "2026-01-04", "everyone", "thread"),
            ),
            SUB + "archive?sort=new&offset=4&limit=50": "[]",
            SUB + "posts/second": substack_post(
                "second", "Second post", "2026-09-20", "<p>%s</p>" % LONG_PARAGRAPH
            ),
            SUB + "posts/paid-one": substack_post(
                "paid-one", "Paid one", "2026-09-10", "<p>Teaser.</p>", "only_paid"
            ),
            SUB + "posts/first": substack_post(
                "first", "First post", "2026-01-05", "<p>%s</p>" % LONG_PARAGRAPH
            ),
        }
        pages.update(extra)
        return FakeWeb(pages)

    def profile_for(self):
        return self.profile("  - substack: news.example.com\n    min_gap_seconds: 0\n")

    def test_every_post_in_the_archive_is_saved_whole(self):
        web = self.web()
        code, out, err = self.run_main(web, self.profile_for())
        self.assertEqual(code, 0, err)
        self.assertEqual(
            saved(self.archive),
            ["2026-01-05-first-post.md", "2026-09-10-paid-one.md", "2026-09-20-second-post.md"],
        )
        body = self.read("2026-01-05-first-post.md")
        self.assertIn("Source: https://news.example.com/p/first (published 2026-01-05)", body)
        self.assertIn(LONG_PARAGRAPH.strip(), body)
        self.assertNotIn(SUB + "posts/a-thread", web.calls)  # a thread is not a post
        self.assertIn("3 posts, 3 new", out)

    def test_a_paid_post_is_flagged_as_a_preview(self):
        code, out, _ = self.run_main(self.web(), self.profile_for())
        self.assertIn("2026-09-10-paid-one.md is for paid subscribers", out)

    def test_a_saved_post_is_not_fetched_again(self):
        profile = self.profile_for()
        self.run_main(self.web(), profile)
        web = self.web()
        code, out, _ = self.run_main(web, profile)
        self.assertEqual(code, 0)
        self.assertFalse([u for u in web.calls if "/posts/" in u])
        self.assertIn("3 already saved", out)

    def test_an_interrupted_run_resumes(self):
        profile = self.profile_for()
        web = self.web(**{SUB + "posts/first": OSError("connection reset")})
        code, out, err = self.run_main(web, profile)
        self.assertEqual(code, 0)
        self.assertIn("1 failed", out)
        self.assertIn("p/first failed: connection reset", err)
        web = self.web()
        self.run_main(web, profile)
        self.assertEqual([u for u in web.calls if "/posts/" in u], [SUB + "posts/first"])

    def test_an_archive_api_that_fails_falls_back_to_the_feed(self):
        feed = rss(
            rss_item(
                "From the feed",
                "https://news.example.com/p/f",
                "Tue, 29 Sep 2026",
                "<p>%s</p>" % LONG_PARAGRAPH,
            )
        )
        for failure in (
            urllib.error.HTTPError("u", 403, "Forbidden", {}, None),
            "<html>not json</html>",
            '{"posts": []}',
        ):
            with self.subTest(failure=str(failure)[:20]):
                web = FakeWeb(
                    {
                        SUB + "archive?sort=new&offset=0&limit=50": failure,
                        "https://news.example.com/feed": feed,
                    }
                )
                code, out, _ = self.run_main(web, self.profile_for(), "--dry-run")
                self.assertEqual(code, 0)
                self.assertIn("reading the RSS feed instead", out)
                self.assertIn("2026-09-29-from-the-feed.md", out)

    def test_a_later_archive_page_that_fails_keeps_what_was_listed(self):
        web = self.web(**{SUB + "archive?sort=new&offset=2&limit=50": "oops"})
        code, out, err = self.run_main(web, self.profile_for())
        self.assertEqual(code, 0)
        self.assertIn("stopped at 2 posts", err)
        self.assertEqual(len(saved(self.archive)), 2)

    def test_a_page_with_no_new_post_ends_the_listing(self):
        same = archive_page(("only", "Only", "2026-02-02", "everyone", "newsletter"))
        web = FakeWeb(
            {
                SUB + "archive?sort=new&offset=0&limit=50": same,
                SUB + "archive?sort=new&offset=1&limit=50": same,
                SUB + "posts/only": substack_post("only", "Only", "2026-02-02", "<p>x</p>"),
            }
        )
        code, out, _ = self.run_main(web, self.profile_for(), "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(sum("archive?" in u for u in web.calls), 2)

    def test_requests_are_spaced_by_the_gap(self):
        clock = [100.0]
        slept = []

        def sleep(seconds):
            slept.append(round(seconds, 3))
            clock[0] += seconds

        pacer = af.Pacer(1)
        with (
            mock.patch.object(af.time, "monotonic", lambda: clock[0]),
            mock.patch.object(af.time, "sleep", sleep),
        ):
            pacer.wait()
            clock[0] += 0.25
            pacer.wait()
            clock[0] += 5
            pacer.wait()
        self.assertEqual(slept, [0.75])

    def test_the_default_gap_is_one_second(self):
        self.assertEqual(af.DEFAULT_GAP_SECONDS, 1)


SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://blog.example.com/guides/ci-reliability</loc><lastmod>2026-09-01</lastmod></url>
<url><loc>https://blog.example.com/guides/ci-reliability/quarantine-results-q3</loc><lastmod>2026-09-03T10:00:00Z</lastmod></url>
<url><loc>https://blog.example.com/guides/test-tooling/a-runner-checklist</loc><lastmod>2026-08-01</lastmod></url>
<url><loc>https://blog.example.com/guides/a-top-level-guide</loc></url>
<url><loc>https://blog.example.com/guides/ci-reliability/thin-page</loc><lastmod>2026-07-01</lastmod></url>
<url><loc>https://blog.example.com/guides/ci-reliability/broken-page</loc><lastmod>2026-06-01</lastmod></url>
<url><loc>https://blog.example.com/about</loc></url>
</urlset>"""


def page(title, body, head="", wrap="article"):
    return (
        "<html><head><title>%s | Example</title>%s</head><body>"
        "<nav><a href='/'>Home</a> Menu Menu</nav><header>Site header</header>"
        "<%s><h1>%s</h1>%s</%s><footer>Footer links</footer></body></html>"
        % (title, head, wrap, title, body, wrap)
    )


BODY = "<p>%s</p><h2>What changed</h2><ul><li>Re-runs</li><li>Time to green</li></ul>" % (
    "A paragraph of a guide that is long enough to count as a page. " * 5
)


class TestSitemap(InProcess):
    def web(self, **extra):
        pages = {
            "https://blog.example.com/sitemap.xml": SITEMAP,
            "https://blog.example.com/guides/ci-reliability/quarantine-results-q3": page(
                "Quarantine results Q3",
                BODY,
                head='<meta property="article:published_time" content="2026-09-02T06:00:00Z">',
            ),
            "https://blog.example.com/guides/test-tooling/a-runner-checklist": page(
                "A runner checklist",
                '<time datetime="2026-07-30">30 July</time>' + BODY,
                wrap="main",
            ),
            "https://blog.example.com/guides/a-top-level-guide": page(
                "A top-level guide", BODY, wrap="div"
            ),
            "https://blog.example.com/guides/ci-reliability/thin-page": page(
                "Thin", "<p>Short.</p>"
            ),
            "https://blog.example.com/guides/ci-reliability/broken-page": OSError("timed out"),
        }
        pages.update(extra)
        return FakeWeb(pages)

    def profile_for(self, extra=""):
        return self.profile(
            "  - sitemap: https://blog.example.com/sitemap.xml\n"
            "    path_prefix: /guides/\n    min_gap_seconds: 0\n" + extra
        )

    def test_pages_under_the_prefix_are_saved_with_their_category(self):
        web = self.web()
        code, out, err = self.run_main(web, self.profile_for())
        self.assertEqual(code, 0, err)
        self.assertEqual(
            saved(self.archive),
            [
                "a-top-level-guide.md",
                "ci-reliability-quarantine-results-q3.md",
                "test-tooling-a-runner-checklist.md",
            ],
        )
        text = self.read("ci-reliability-quarantine-results-q3.md")
        self.assertTrue(text.startswith("# Quarantine results Q3\n"))
        self.assertIn("(published 2026-09-02)", text)
        self.assertIn("Category: ci-reliability\n", text)
        self.assertIn("## What changed\n\n- Re-runs\n- Time to green", text)
        for furniture in ("Menu", "Site header", "Footer links"):
            self.assertNotIn(furniture, text)
        self.assertEqual(text.count("Quarantine results Q3"), 1)
        self.assertNotIn("https://blog.example.com/about", web.calls)
        self.assertNotIn("https://blog.example.com/guides/ci-reliability", web.calls)  # its listing
        index = self.index()
        self.assertEqual(
            index["ci-reliability-quarantine-results-q3.md"]["category"], "ci-reliability"
        )
        self.assertEqual(index["test-tooling-a-runner-checklist.md"]["published"], "2026-07-30")
        self.assertIsNone(index["a-top-level-guide.md"]["category"])
        self.assertIsNone(index["a-top-level-guide.md"]["published"])

    def test_short_pages_are_skipped_and_failed_ones_counted(self):
        code, out, err = self.run_main(self.web(), self.profile_for())
        self.assertEqual(code, 0)
        self.assertIn("thin-page has", out)
        self.assertIn("likely a listing page", out)
        self.assertIn("1 folder page(s)", out)
        self.assertIn("1 skipped, 1 failed", out)
        self.assertIn("broken-page failed: timed out", err)

    def test_the_sitemap_date_is_the_last_resort(self):
        body_only = "<html><body><h1>Plain</h1>%s</body></html>" % BODY
        web = self.web(
            **{"https://blog.example.com/guides/ci-reliability/quarantine-results-q3": body_only}
        )
        self.run_main(web, self.profile_for())
        self.assertEqual(
            self.index()["ci-reliability-quarantine-results-q3.md"]["published"], "2026-09-03"
        )

    def test_max_pages_keeps_the_newest(self):
        web = self.web()
        code, out, _ = self.run_main(web, self.profile_for("    max_pages: 1\n"))
        self.assertEqual(saved(self.archive), ["ci-reliability-quarantine-results-q3.md"])
        self.assertIn("keeping the 1 newest", out)

    def test_a_saved_page_is_not_fetched_again(self):
        profile = self.profile_for()
        self.run_main(self.web(), profile)
        web = self.web()
        code, out, _ = self.run_main(web, profile)
        self.assertNotIn(
            "https://blog.example.com/guides/ci-reliability/quarantine-results-q3", web.calls
        )
        self.assertIn("3 already saved", out)

    def test_a_sitemap_index_and_a_gzipped_sitemap(self):
        index = (
            '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            "<sitemap><loc>https://blog.example.com/sitemap-guides.xml.gz</loc></sitemap>"
            "<sitemap><loc>https://blog.example.com/sitemap-missing.xml</loc></sitemap>"
            "</sitemapindex>"
        )
        web = self.web(
            **{
                "https://blog.example.com/sitemap.xml": index,
                "https://blog.example.com/sitemap-guides.xml.gz": gzip.compress(SITEMAP.encode()),
            }
        )
        code, out, err = self.run_main(web, self.profile_for())
        self.assertEqual(code, 0, err)
        self.assertIn("sitemap https://blog.example.com/sitemap-missing.xml failed", err)
        self.assertEqual(len(saved(self.archive)), 3)

    def test_a_response_that_is_not_a_sitemap_fails_the_source(self):
        for body in ("<html>no</html>", "", '<?xml version="1.0"?><rss></rss>', "<urlset"):
            with self.subTest(body=body):
                web = FakeWeb({"https://blog.example.com/sitemap.xml": body})
                code, _, err = self.run_main(web, self.profile_for(), "--dry-run")
                self.assertNotEqual(code, 0)
                self.assertIn("sitemap.xml failed", err)

    def test_an_empty_sitemap_saves_nothing(self):
        empty = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
        code, out, _ = self.run_main(
            FakeWeb({"https://blog.example.com/sitemap.xml": empty}), self.profile_for()
        )
        self.assertEqual(code, 0)
        self.assertIn("0 pages under /guides/", out)

    def test_dry_run_fetches_no_page(self):
        web = self.web()
        code, out, _ = self.run_main(web, self.profile_for(), "--dry-run")
        self.assertEqual(web.calls, ["https://blog.example.com/sitemap.xml"])
        self.assertIn("would fetch", out)
        self.assertFalse(os.path.exists(self.archive))


MEDIUM_STORY = """<!DOCTYPE html><html><head><title>{title}</title></head><body>
<article class="h-entry"><header><h1 class="p-name">{title}</h1></header>
<section data-field="subtitle" class="p-summary">A subtitle</section>
<section data-field="body" class="e-content"><section class="section"><div><div>
{title_graf}<p class="graf graf--p">{text}</p></div></div></section></section>
<footer><p>By <a class="p-author h-card" href="https://medium.com/@example-author">
Example Author</a> {time}</p><p>
<a href="https://medium.com/@example-author/{slug}" class="p-canonical">Canonical link</a></p>
</footer></article></body></html>"""


def medium_file(
    title, text, published="2025-03-04T10:00:00.000Z", has_title=True, slug="a-post-1a2b"
):
    return MEDIUM_STORY.format(
        title=title,
        text=text,
        slug=slug,
        title_graf='<h3 class="graf graf--h3 graf--leading graf--title">%s</h3>' % title
        if has_title
        else "",
        time='on <time class="dt-published" datetime="%s">March 4</time>.' % published
        if published
        else "",
    )


class TestMediumExport(InProcess):
    def export(self, files, as_zip=False):
        root = os.path.join(self.dir, "medium-export")
        for rel, body in files.items():
            path = os.path.join(root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)
        if not as_zip:
            return root
        zpath = os.path.join(self.dir, "medium-export.zip")
        with zipfile.ZipFile(zpath, "w") as zf:
            for rel, body in files.items():
                zf.writestr("medium-export-1a2b/" + rel, body)
        return zpath

    FILES = {
        "posts/2025-03-04_A-real-story-1a2b.html": medium_file("A real story", "Story text."),
        "posts/draft_Unfinished-3c4d.html": medium_file("Unfinished", "Draft text."),
        "posts/2025-03-05_Nice-post--5e6f.html": medium_file(
            "Nice post!", "Agreed.", has_title=False
        ),
        "posts/2025-03-06_Unpublished-7a8b.html": medium_file("Unpublished", "x", published=None),
        "posts/2025-03-07_Odd-9c0d.html": "<html><body><p>Not a Medium post.</p></body></html>",
        "profile/profile.html": "<html><body>Profile</body></html>",
        "README.txt": "not a post",
    }

    def test_published_stories_are_kept_and_the_rest_skipped(self):
        for as_zip in (False, True):
            with self.subTest(as_zip=as_zip):
                shutil.rmtree(self.archive, True)
                path = self.export(self.FILES, as_zip=as_zip)
                code, out, err = self.run_main(None, self.profile("  - medium_export: %s\n" % path))
                self.assertEqual(code, 0, err)
                self.assertEqual(saved(self.archive), ["2025-03-04-a-real-story.md"])
                text = self.read("2025-03-04-a-real-story.md")
                self.assertIn(
                    "Source: https://medium.com/@example-author/a-post-1a2b (published 2025-03-04)",
                    text,
                )
                self.assertTrue(text.endswith("\nStory text.\n"), text)
                self.assertIn("skipped 2 draft(s), 1 response(s), 1 unrecognised file(s)", out)
                self.assertIn("Odd-9c0d.html: not a Medium post", out)

    def test_an_export_with_no_posts_or_no_such_path_fails_the_source(self):
        not_export = os.path.join(self.dir, "notes.txt")
        with open(not_export, "w") as f:
            f.write("hello")
        for path, needle in (
            (self.export({"profile/profile.html": "<html></html>"}), "no posts/*.html"),
            (os.path.join(self.dir, "missing.zip"), "not found"),
            (not_export, "neither a zip file nor a folder"),
        ):
            with self.subTest(path=path):
                code, _, err = self.run_main(None, self.profile("  - medium_export: %s\n" % path))
                self.assertNotEqual(code, 0)
                self.assertIn(needle, err)

    def test_a_broken_zip_fails_the_source(self):
        bad = os.path.join(self.dir, "bad.zip")
        with open(bad, "wb") as f:
            f.write(b"PK\x03\x04 truncated")
        code, _, err = self.run_main(None, self.profile("  - medium_export: %s\n" % bad))
        self.assertNotEqual(code, 0)
        self.assertNotIn("Traceback", err)


POST_URL = "https://social.example.com/feed/update/urn:li:activity:"
SHARES = (
    "Date,ShareLink,ShareCommentary,SharedUrl,MediaUrl,Visibility\n"
    "2026-05-02 09:10:11," + POST_URL + "1,"
    '"Three things I learned shipping our CI dashboard this year.\n\n'
    'First, flaky tests are a team problem.",,,MEMBER_NETWORK\n'
    "2026-05-03 10:00:00," + POST_URL + "2,,https://example.com/a,,MEMBER_NETWORK\n"
    "2026-04-01 08:00:00," + POST_URL + '3,"Short note, with a ""quote"".",,,MEMBER_NETWORK\n'
)


class TestLinkedInExport(InProcess):
    def export(self, name, body, folder="Complete_LinkedInDataExport"):
        root = os.path.join(self.dir, "linkedin")
        path = os.path.join(root, folder, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        return root

    def test_each_post_with_text_is_saved(self):
        root = self.export("Shares.csv", "﻿" + SHARES)
        code, out, err = self.run_main(None, self.profile("  - linkedin_export: %s\n" % root))
        self.assertEqual(code, 0, err)
        self.assertEqual(
            saved(self.archive),
            [
                "2026-04-01-short-note-with-a-quote.md",
                "2026-05-02-three-things-i-learned-shipping-our-ci-dashboard.md",
            ],
        )
        text = self.read("2026-05-02-three-things-i-learned-shipping-our-ci-dashboard.md")
        self.assertIn("urn:li:activity:1 (published 2026-05-02)", text)
        self.assertIn("this year.\n\nFirst, flaky tests are a team problem.", text)
        self.assertIn("skipped 1 rows with no text", out)
        self.assertNotIn("preview", out)  # a short post is not a paid preview

    def test_a_note_line_before_the_header_and_a_zip(self):
        zpath = os.path.join(self.dir, "export.zip")
        with zipfile.ZipFile(zpath, "w") as zf:
            zf.writestr("Shares.csv", "Notes:\nThis file holds your shares.\n" + SHARES)
        code, out, err = self.run_main(None, self.profile("  - linkedin_export: %s\n" % zpath))
        self.assertEqual(code, 0, err)
        self.assertEqual(len(saved(self.archive)), 2)

    def test_an_unrecognised_or_empty_csv_fails_the_source(self):
        for body in ("Name,Email\nA,b@example.com\n", "", "a\x00b\n"):
            with self.subTest(body=body):
                root = self.export("Shares.csv", body)
                code, out, err = self.run_main(
                    None, self.profile("  - linkedin_export: %s\n" % root)
                )
                self.assertNotEqual(code, 0)
                self.assertIn("[skip]", out)
                self.assertIn("no Shares.csv with a ShareCommentary column", err)
                self.assertNotIn("Traceback", err)

    def test_an_export_without_shares_fails_the_source(self):
        root = self.export("Connections.csv", "First Name\n")
        code, _, err = self.run_main(None, self.profile("  - linkedin_export: %s\n" % root))
        self.assertNotEqual(code, 0)
        self.assertIn("no Shares.csv", err)


class TestTagIndex(InProcess):
    def feed(self):
        path = os.path.join(self.dir, "feed.xml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                rss(
                    rss_item(
                        "Post one",
                        "https://blog.example.com/one",
                        "Tue, 29 Sep 2026",
                        "<p>%s</p>" % LONG_PARAGRAPH,
                    )
                )
            )
        return self.profile("  - rss: file://%s\n" % path)

    def test_every_saved_post_gets_an_index_entry(self):
        code, out, _ = self.run_main(af.fetch, self.feed())
        self.assertEqual(code, 0)
        entry = self.index()["2026-09-29-post-one.md"]
        self.assertEqual(entry["url"], "https://blog.example.com/one")
        self.assertEqual(entry["published"], "2026-09-29")
        self.assertIsNone(entry["category"])
        self.assertIsNone(entry["content_type"])
        self.assertGreater(entry["words"], 300)
        self.assertIn("1 without a content type; run archive_tag.py", out)

    def test_a_hand_added_file_gets_an_entry_and_a_type_survives_refresh(self):
        profile = self.feed()
        self.run_main(af.fetch, profile)
        with open(os.path.join(self.archive, "my-linkedin-post.txt"), "w") as f:
            f.write("A post I pasted by hand.")
        path = os.path.join(self.archive, ".tags.json")
        with open(path) as f:
            data = json.load(f)
        data["posts"]["2026-09-29-post-one.md"]["content_type"] = "how-to"
        with open(path, "w") as f:
            json.dump(data, f)
        self.run_main(af.fetch, profile, "--refresh")
        index = self.index()
        self.assertEqual(index["2026-09-29-post-one.md"]["content_type"], "how-to")
        self.assertEqual(
            index["my-linkedin-post.txt"],
            {
                "title": None,
                "url": None,
                "published": None,
                "category": None,
                "content_type": None,
                "words": 6,
            },
        )

    def test_a_dry_run_writes_no_index(self):
        self.run_main(af.fetch, self.feed(), "--dry-run")
        self.assertFalse(os.path.exists(self.archive))

    def test_an_unreadable_index_stops_with_a_message(self):
        os.makedirs(self.archive)
        for body in ("{not json", '{"posts": []}', "[]"):
            with self.subTest(body=body):
                with open(os.path.join(self.archive, ".tags.json"), "w") as f:
                    f.write(body)
                code, _, err = self.run_main(af.fetch, self.feed())
                self.assertNotEqual(code, 0)
                self.assertIn("tag index", err)

    def test_the_header_is_read_back(self):
        post = {
            "title": "T",
            "url": "https://blog.example.com/guides/x/t",
            "published": "2026-01-02",
            "category": "x",
            "text": "Body.",
        }
        self.assertEqual(
            af.read_header(af.render(post)),
            ("T", "https://blog.example.com/guides/x/t", "2026-01-02", "x"),
        )
        self.assertEqual(af.read_header("just text"), (None, None, None, None))


class TestArchiveSavedAndFailed(InProcess):
    """Archive sources: already-saved by URL, failed
    sources, header-only categories, origins, paid audiences, boundaries."""

    LONG = "https://blog.example.com/guides/test-tooling/how-to-read-a-flaky-test-report-when-the-failures-look-the-same-"

    def sitemap(self, *locs, lastmod="2026-09-01"):
        return (
            '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join("<url><loc>%s</loc><lastmod>%s</lastmod></url>" % (u, lastmod) for u in locs)
            + "</urlset>"
        )

    def profile_for(self, extra=""):
        return self.profile(
            "  - sitemap: https://blog.example.com/sitemap.xml\n"
            "    path_prefix: /guides/\n    min_gap_seconds: 0\n" + extra
        )

    def test_a_new_post_whose_name_is_taken_is_saved_under_its_own_name(self):
        one, two = self.LONG + "part-one", self.LONG + "part-two"
        pages = {
            one: page("Part ONE", BODY + "<p>Part ONE text.</p>"),
            two: page("Part TWO", BODY + "<p>Part TWO text.</p>"),
        }
        web = FakeWeb(dict(pages, **{"https://blog.example.com/sitemap.xml": self.sitemap(one)}))
        code, out, _ = self.run_main(web, self.profile_for())
        self.assertIn("1 new", out)
        web = FakeWeb(
            dict(pages, **{"https://blog.example.com/sitemap.xml": self.sitemap(two, one)})
        )
        code, out, _ = self.run_main(web, self.profile_for())
        self.assertEqual(code, 0)
        self.assertIn("1 new, 1 already saved", out)
        names = saved(self.archive)
        self.assertEqual(len(names), 2)
        texts = [self.read(n) for n in names]
        self.assertTrue(any("Part TWO text." in t for t in texts))
        self.assertTrue(any("Part ONE text." in t for t in texts))
        self.assertEqual({e["url"] for e in self.index().values()}, {one, two})
        web = FakeWeb(
            dict(pages, **{"https://blog.example.com/sitemap.xml": self.sitemap(two, one)})
        )
        code, out, _ = self.run_main(web, self.profile_for())
        self.assertIn("0 new, 2 already saved", out)
        self.assertEqual(web.calls, ["https://blog.example.com/sitemap.xml"])

    def test_a_hand_added_file_without_a_url_is_matched_by_name(self):
        os.makedirs(self.archive)
        with open(os.path.join(self.archive, "test-tooling-a-guide.md"), "w") as f:
            f.write("my own copy")
        url = "https://blog.example.com/guides/test-tooling/a-guide"
        web = FakeWeb(
            {"https://blog.example.com/sitemap.xml": self.sitemap(url), url: page("A", BODY)}
        )
        code, out, _ = self.run_main(web, self.profile_for())
        self.assertIn("0 new, 1 already saved", out)
        self.assertEqual(self.read("test-tooling-a-guide.md"), "my own copy")

    def test_a_source_whose_every_page_failed_is_a_failed_source(self):
        a = "https://blog.example.com/guides/ci-reliability/a"
        b = "https://blog.example.com/guides/ci-reliability/b"
        error = urllib.error.HTTPError(a, 500, "Server Error", {}, None)
        web = FakeWeb(
            {"https://blog.example.com/sitemap.xml": self.sitemap(a, b), a: error, b: error}
        )
        code, out, err = self.run_main(web, self.profile_for())
        self.assertNotEqual(code, 0)
        self.assertIn("1 source(s) failed", out)
        self.assertIn("Every archive source failed", err)

    def test_pages_on_another_host_or_scheme_are_never_read(self):
        # The prefix is a real local folder, so a file:// URL under it would
        # otherwise be inside the prefix and read from disk.
        prefix = os.path.join(self.dir, "guides") + "/"
        os.makedirs(prefix + "ci-reliability")
        secret = "file://" + prefix + "ci-reliability/secret.html"
        with open(prefix + "ci-reliability/secret.html", "w") as f:
            f.write(page("Secret", BODY))
        good = "https://blog.example.com" + prefix + "ci-reliability/good"
        locs = (
            secret,
            "http://blog.example.com" + prefix + "ci-reliability/plain-http",
            "https://other.example.com" + prefix + "ci-reliability/elsewhere",
            good,
        )
        web = FakeWeb(
            {
                "https://blog.example.com/sitemap.xml": self.sitemap(*locs),
                good: page("Good", BODY),
                secret: page("Secret", BODY),
            }
        )
        profile = self.profile(
            "  - sitemap: https://blog.example.com/sitemap.xml\n"
            "    path_prefix: %s\n    min_gap_seconds: 0\n" % prefix
        )
        code, out, _ = self.run_main(web, profile)
        self.assertEqual(code, 0)
        self.assertEqual(saved(self.archive), ["ci-reliability-good.md"])
        self.assertIn("3 page(s) not on the sitemap's own scheme and host", out)
        self.assertEqual(web.calls, ["https://blog.example.com/sitemap.xml", good])

    def test_a_nested_sitemap_on_another_host_is_skipped(self):
        index = (
            '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            "<sitemap><loc>https://other.example.com/sitemap.xml</loc></sitemap></sitemapindex>"
        )
        web = FakeWeb({"https://blog.example.com/sitemap.xml": index})
        code, out, _ = self.run_main(web, self.profile_for())
        self.assertIn("[skip] nested sitemap https://other.example.com/sitemap.xml", out)
        self.assertNotIn("https://other.example.com/sitemap.xml", web.calls)

    def test_a_file_sitemap_may_list_file_pages(self):
        d = os.path.join(self.dir, "site", "guides", "ci-reliability")
        os.makedirs(d)
        with open(os.path.join(d, "local.html"), "w") as f:
            f.write(page("Local", BODY))
        loc = "file://" + os.path.join(d, "local.html")
        sm = os.path.join(self.dir, "site", "sitemap.xml")
        with open(sm, "w") as f:
            f.write(self.sitemap(loc))
        prefix = os.path.join(self.dir, "site", "guides") + "/"
        code, out, err = self.run_main(
            af.fetch,
            self.profile(
                "  - sitemap: file://%s\n    path_prefix: %s\n    min_gap_seconds: 0\n"
                % (sm, prefix)
            ),
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(saved(self.archive), ["ci-reliability-local-html.md"])

    def test_the_prefix_page_itself_is_not_a_post(self):
        prefix_page = "https://blog.example.com/guides/"
        web = FakeWeb({"https://blog.example.com/sitemap.xml": self.sitemap(prefix_page)})
        code, out, _ = self.run_main(web, self.profile_for())
        self.assertIn("0 pages under /guides/", out)
        self.assertNotIn(prefix_page, web.calls)

    def test_two_hundred_characters_is_a_page_and_one_ninety_nine_is_not(self):
        a = "https://blog.example.com/guides/ci-reliability/exact"
        b = "https://blog.example.com/guides/ci-reliability/short"
        bare = "<html><head><title>T</title></head><body><article><p>%s</p></article></body></html>"
        web = FakeWeb(
            {
                "https://blog.example.com/sitemap.xml": self.sitemap(a, b),
                a: bare % ("x" * 200),
                b: bare % ("y" * 199),
            }
        )
        code, out, _ = self.run_main(web, self.profile_for())
        self.assertEqual(saved(self.archive), ["ci-reliability-exact.md"])
        self.assertIn("short has 199 characters", out)
        self.assertEqual(af.MIN_PAGE_CHARS, 200)

    def test_max_pages_equal_to_the_pages_keeps_them_all(self):
        locs = ["https://blog.example.com/guides/ci-reliability/p%d" % i for i in range(3)]
        web = FakeWeb(
            dict(
                {u: page("P", BODY) for u in locs},
                **{"https://blog.example.com/sitemap.xml": self.sitemap(*locs)},
            )
        )
        code, out, _ = self.run_main(web, self.profile_for("    max_pages: 3\n"))
        self.assertEqual(len(saved(self.archive)), 3)
        self.assertNotIn("keeping the", out)

    def test_a_sitemap_index_is_followed_two_levels_down(self):
        def index(child):
            return (
                '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                "<sitemap><loc>%s</loc></sitemap></sitemapindex>" % child
            )

        base = "https://blog.example.com/"
        pg = base + "guides/ci-reliability/deep"
        for depth, expect in ((2, 1), (3, 0)):
            with self.subTest(depth=depth):
                shutil.rmtree(self.archive, True)
                pages = {pg: page("Deep", BODY)}
                names = ["sitemap.xml"] + ["s%d.xml" % i for i in range(1, depth + 1)]
                for here, child in zip(names, names[1:]):
                    pages[base + here] = index(base + child)
                pages[base + names[-1]] = self.sitemap(pg)
                code, out, _ = self.run_main(FakeWeb(pages), self.profile_for())
                self.assertEqual(
                    len(saved(self.archive)) if os.path.isdir(self.archive) else 0, expect
                )

    def test_only_paid_and_founding_audiences_are_paid(self):
        for audience, paid in (
            ("only_paid", True),
            ("founding", True),
            ("only_free", False),
            ("everyone", False),
        ):
            with self.subTest(audience=audience):
                web = FakeWeb(
                    {
                        SUB + "posts/x": substack_post(
                            "x", "X", "2026-01-01", "<p>%s</p>" % LONG_PARAGRAPH, audience
                        )
                    }
                )
                with mock.patch.object(af, "fetch", web):
                    post = af._substack_post("https://news.example.com", {"slug": "x"}, af.Pacer(0))
                self.assertIs(post["paid"], paid)

    def test_a_category_line_in_a_post_body_is_not_its_category(self):
        path = os.path.join(self.dir, "feed.xml")
        with open(path, "w") as f:
            f.write(
                rss(
                    rss_item(
                        "Body line",
                        "https://blog.example.com/b",
                        "Tue, 29 Sep 2026",
                        "<p>Category: tooling</p><p>%s</p>" % LONG_PARAGRAPH,
                    )
                )
            )
        self.run_main(af.fetch, self.profile("  - rss: file://%s\n" % path))
        self.assertIsNone(self.index()["2026-09-29-body-line.md"]["category"])

    def test_the_header_is_only_the_block_below_the_title(self):
        self.assertEqual(
            af.read_header("# T\n\nSource: https://a.example.com/1\n\nCategory: tooling\n"),
            ("T", "https://a.example.com/1", None, None),
        )
        self.assertEqual(
            af.read_header(
                "# T\n\nSource: https://a.example.com/1 (published 2026-01-01)\n"
                "Source: https://b.example.com/2 (published 2026-02-02)\nCategory: x\n\nbody\n"
            ),
            ("T", "https://a.example.com/1", "2026-01-01", "x"),
        )
        self.assertEqual(
            af.read_header("Source: https://a.example.com/1\n"), (None, None, None, None)
        )


class TestArchiveUrlKeysAndClashes(InProcess):
    """URL keys, Substack's two URLs, failed sitemap
    sources, link-less name clashes, audience case, renamed files."""

    sitemap = TestArchiveSavedAndFailed.sitemap
    profile_for = TestArchiveSavedAndFailed.profile_for

    def test_a_url_key_drops_tracking_and_case_but_keeps_the_rest(self):
        self.assertEqual(
            af.url_key(
                "HTTPS://Blog.Example.com/guides/x/a/?utm_source=n&id=3&ref=hn&Source=x#top"
            ),
            "https://blog.example.com/guides/x/a?id=3",
        )
        self.assertNotEqual(
            af.url_key("https://b.example.com/a?id=3"), af.url_key("https://b.example.com/a?id=4")
        )
        self.assertEqual(
            af.url_key("https://b.example.com/a"), af.url_key("https://b.example.com/a/")
        )

    def test_the_same_page_under_a_tracking_url_is_not_saved_twice(self):
        clean = "https://blog.example.com/guides/ci-reliability/a"
        noisy = "https://Blog.Example.com/guides/ci-reliability/a/?utm_source=news#top"
        p = page("A", BODY)
        self.run_main(
            FakeWeb({"https://blog.example.com/sitemap.xml": self.sitemap(clean), clean: p}),
            self.profile_for(),
        )
        web = FakeWeb({"https://blog.example.com/sitemap.xml": self.sitemap(noisy), noisy: p})
        code, out, _ = self.run_main(web, self.profile_for())
        self.assertIn("0 new, 1 already saved", out)
        self.assertEqual(len(saved(self.archive)), 1)

    def test_a_substack_post_served_under_another_url_is_not_saved_again(self):
        listing = archive_page(("slug", "A post", "2026-03-03", "everyone", "newsletter"))
        served = json.dumps(
            {
                "slug": "slug",
                "title": "A post",
                "post_date": "2026-03-03T08:00:00.000Z",
                "audience": "everyone",
                "canonical_url": "https://www.news.example.com/p/a-post-renamed",
                "body_html": "<p>%s</p>" % LONG_PARAGRAPH,
            }
        )
        pages = {
            SUB + "archive?sort=new&offset=0&limit=50": listing,
            SUB + "archive?sort=new&offset=1&limit=50": "[]",
            SUB + "posts/slug": served,
        }
        profile = self.profile("  - substack: news.example.com\n    min_gap_seconds: 0\n")
        self.run_main(FakeWeb(pages), profile)
        entry = self.index()["2026-03-03-a-post.md"]
        self.assertEqual(entry["url"], "https://www.news.example.com/p/a-post-renamed")
        self.assertEqual(entry["listed_url"], "https://news.example.com/p/slug")
        web = FakeWeb(pages)
        code, out, _ = self.run_main(web, profile)
        self.assertIn("1 already saved", out)
        self.assertNotIn(SUB + "posts/slug", web.calls)

    def test_a_sitemap_index_none_of_whose_sitemaps_reads_is_a_failed_source(self):
        index = (
            '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            "<sitemap><loc>https://blog.example.com/s1.xml</loc></sitemap>"
            "<sitemap><loc>https://other.example.com/s2.xml</loc></sitemap></sitemapindex>"
        )
        web = FakeWeb(
            {
                "https://blog.example.com/sitemap.xml": index,
                "https://blog.example.com/s1.xml": OSError("timed out"),
            }
        )
        code, out, err = self.run_main(web, self.profile_for())
        self.assertNotEqual(code, 0)
        self.assertIn("1 source(s) failed", out)
        self.assertIn("none of the 2 sitemap(s)", err)

    def test_a_sitemap_whose_every_page_is_off_origin_is_a_failed_source(self):
        www = "https://www.blog.example.com/guides/ci-reliability/a"
        web = FakeWeb({"https://blog.example.com/sitemap.xml": self.sitemap(www)})
        code, out, err = self.run_main(web, self.profile_for())
        self.assertNotEqual(code, 0)
        self.assertIn("another scheme or host", err)

    def test_the_host_is_compared_in_any_case(self):
        upper = "https://BLOG.Example.com/guides/ci-reliability/a"
        web = FakeWeb(
            {"https://blog.example.com/sitemap.xml": self.sitemap(upper), upper: page("A", BODY)}
        )
        code, out, _ = self.run_main(web, self.profile_for())
        self.assertEqual(code, 0)
        self.assertEqual(saved(self.archive), ["ci-reliability-a.md"])

    def test_a_thin_page_is_a_skip_not_a_failure(self):
        thin = "https://blog.example.com/guides/ci-reliability/thin"
        broken = "https://blog.example.com/guides/ci-reliability/broken"
        web = FakeWeb(
            {
                "https://blog.example.com/sitemap.xml": self.sitemap(thin, broken),
                thin: page("Thin", "<p>Short.</p>"),
                broken: urllib.error.HTTPError(broken, 500, "Server Error", {}, None),
            }
        )
        code, out, _ = self.run_main(web, self.profile_for())
        self.assertEqual(code, 0)
        self.assertIn("1 skipped, 1 failed", out)
        self.assertIn("0 source(s) failed", out)

    def test_two_link_less_posts_with_one_name_are_both_saved(self):
        def feed(*titles):
            path = os.path.join(self.dir, "feed.xml")
            items = "".join(
                "<item><title>%s</title><pubDate>Tue, 29 Sep 2026</pubDate>"
                "<description>d</description><content:encoded><![CDATA[<p>%s %s</p>]]>"
                "</content:encoded></item>" % (t, t, LONG_PARAGRAPH)
                for t in titles
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(rss(items))
            return self.profile("  - rss: file://%s\n" % path)

        long = "A very long title about flaky test quarantine that runs past sixty characters"
        self.run_main(af.fetch, feed(long + " one"))
        code, out, _ = self.run_main(af.fetch, feed(long + " two", long + " one"))
        self.assertEqual(code, 0)
        self.assertEqual(len(saved(self.archive)), 2)
        self.assertIn("1 new, 1 already saved", out)
        titles = sorted(self.read(n).split("\n", 1)[0] for n in saved(self.archive))
        self.assertEqual(titles, ["# " + long + " one", "# " + long + " two"])
        code, out, _ = self.run_main(af.fetch, feed(long + " two", long + " one"))
        self.assertIn("0 new, 2 already saved", out)

    def test_audience_case_and_absence(self):
        for audience, paid in (("Only_Paid", True), ("FOUNDING", True), (None, False)):
            with self.subTest(audience=audience):
                body = {"slug": "x", "title": "X", "body_html": "<p>t</p>"}
                if audience:
                    body["audience"] = audience
                with mock.patch.object(af, "fetch", FakeWeb({SUB + "posts/x": json.dumps(body)})):
                    post = af._substack_post("https://news.example.com", {"slug": "x"}, af.Pacer(0))
                self.assertIs(post["paid"], paid)

    def test_a_renamed_file_is_still_found_by_its_url(self):
        url = "https://blog.example.com/guides/ci-reliability/a"
        pages = {"https://blog.example.com/sitemap.xml": self.sitemap(url), url: page("A", BODY)}
        self.run_main(FakeWeb(pages), self.profile_for())
        os.rename(
            os.path.join(self.archive, "ci-reliability-a.md"),
            os.path.join(self.archive, "my-name.md"),
        )
        code, out, _ = self.run_main(FakeWeb(pages), self.profile_for())
        self.assertIn("0 new, 1 already saved", out)
        self.assertEqual(saved(self.archive), ["my-name.md"])

    def test_the_first_source_line_wins_even_without_a_date(self):
        text = (
            "# T\n\nSource: https://a.example.com/1\n"
            "Source: https://b.example.com/2 (published 2026-02-02)\n\nbody\n"
        )
        self.assertEqual(af.read_header(text), ("T", "https://a.example.com/1", None, None))


class TestArchiveOneSidedClashes(InProcess):
    """Name clashes with one URL, URL keys, origins and nested sitemaps."""

    sitemap = TestArchiveSavedAndFailed.sitemap
    profile_for = TestArchiveSavedAndFailed.profile_for

    def feed(self, *items):
        path = os.path.join(self.dir, "feed.xml")
        body = ""
        for title, link in items:
            body += "<item><title>%s</title>%s<pubDate>Tue, 29 Sep 2026</pubDate>" % (
                title,
                "<link>%s</link>" % link if link else "",
            )
            body += "<content:encoded><![CDATA[<p>%s %s</p>]]></content:encoded></item>" % (
                title,
                LONG_PARAGRAPH,
            )
        with open(path, "w", encoding="utf-8") as f:
            f.write(rss(body))
        return self.profile("  - rss: file://%s\n" % path)

    def titles(self):
        return sorted(self.read(n).split("\n", 1)[0] for n in saved(self.archive))

    def test_the_reported_linked_then_link_less_case_saves_both(self):
        code, out, _ = self.run_main(af.fetch, self.feed(("Hello?", "https://blog.example.com/x")))
        self.assertIn("1 new", out)
        code, out, _ = self.run_main(af.fetch, self.feed(("Hello!", None)))
        self.assertIn("1 new, 0 already saved", out)
        self.assertEqual(self.titles(), ["# Hello!", "# Hello?"])

    def test_link_less_then_linked_with_another_title_saves_both(self):
        self.run_main(af.fetch, self.feed(("Hello!", None)))
        code, out, _ = self.run_main(af.fetch, self.feed(("Hello?", "https://blog.example.com/x")))
        self.assertIn("1 new, 0 already saved", out)
        self.assertEqual(self.titles(), ["# Hello!", "# Hello?"])

    def test_the_same_title_with_a_link_added_or_lost_is_the_same_post(self):
        self.run_main(af.fetch, self.feed(("Hello", None)))
        code, out, _ = self.run_main(af.fetch, self.feed(("Hello", "https://blog.example.com/x")))
        self.assertIn("0 new, 1 already saved", out)
        shutil.rmtree(self.archive)
        self.run_main(af.fetch, self.feed(("Hello", "https://blog.example.com/x")))
        code, out, _ = self.run_main(af.fetch, self.feed(("Hello", None)))
        self.assertIn("0 new, 1 already saved", out)
        self.assertEqual(len(saved(self.archive)), 1)

    def test_a_hand_file_without_a_header_is_already_saved(self):
        os.makedirs(self.archive)
        with open(os.path.join(self.archive, "2026-09-29-hello.md"), "w") as f:
            f.write("pasted by hand, no title line")
        for link in (None, "https://blog.example.com/x"):
            with self.subTest(link=link):
                code, out, _ = self.run_main(af.fetch, self.feed(("Hello", link)))
                self.assertIn("0 new, 1 already saved", out)
                self.assertEqual(saved(self.archive), ["2026-09-29-hello.md"])

    def test_url_keys_fold_scheme_default_port_and_escape_case(self):
        same = (
            "https://blog.example.com/a%2fb",
            "http://blog.example.com/a%2Fb",
            "https://blog.example.com:443/a%2Fb/",
            "http://BLOG.example.com:80/a%2fb",
        )
        self.assertEqual(len({af.url_key(u) for u in same}), 1)
        self.assertNotEqual(
            af.url_key("https://blog.example.com:8443/a"), af.url_key("https://blog.example.com/a")
        )

    def test_an_explicit_default_port_is_the_same_origin(self):
        sitemap = "https://blog.example.com/sitemap.xml"
        for loc, same in (
            ("https://blog.example.com:443/guides/a", True),
            ("https://BLOG.example.com/guides/a", True),
            ("https://blog.example.com:8443/guides/a", False),
            ("http://blog.example.com/guides/a", False),
        ):
            with self.subTest(loc=loc):
                self.assertIs(af.same_origin(loc, sitemap), same)
        self.assertTrue(
            af.same_origin("http://blog.example.com:80/a", "http://blog.example.com/s.xml")
        )

    def test_an_empty_sitemap_index_is_zero_pages_not_a_failure(self):
        empty = '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>'
        code, out, _ = self.run_main(
            FakeWeb({"https://blog.example.com/sitemap.xml": empty}), self.profile_for()
        )
        self.assertEqual(code, 0)
        self.assertIn("0 pages under /guides/", out)
        self.assertIn("0 source(s) failed", out)

    def test_a_sitemap_past_the_depth_limit_gets_a_notice(self):
        def index(child):
            return (
                '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                "<sitemap><loc>%s</loc></sitemap></sitemapindex>" % child
            )

        base = "https://blog.example.com/"
        pg = base + "guides/ci-reliability/top"
        pages = {
            base + "sitemap.xml": index(base + "level-1.xml").replace(
                "</sitemapindex>", "<sitemap><loc>%sflat.xml</loc></sitemap></sitemapindex>" % base
            ),
            base + "flat.xml": self.sitemap(pg),
            pg: page("Top", BODY),
            base + "level-1.xml": index(base + "level-2.xml"),
            base + "level-2.xml": index(base + "level-3.xml"),
        }
        code, out, _ = self.run_main(FakeWeb(pages), self.profile_for())
        self.assertIn(
            "[skip] nested sitemap https://blog.example.com/level-3.xml: more than two levels down",
            out,
        )
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
