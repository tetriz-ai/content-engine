# Copyright 2026 Workloom Solutions Private Limited
# SPDX-License-Identifier: MIT
"""
Unit tests for competitor-blog-scan.py, with every fetch stubbed: RSS and
Atom parsing, the feed-body checks, the lookback and undated rules, and
per-feed failure.

Run: python3 -m unittest discover -s tests
"""

import _guard  # noqa: F401  (first: isolates HOME, keys and network)
import importlib.util
import os
import socket
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "competitor_blog_scan", os.path.join(HERE, "..", "competitor-blog-scan.py")
)
cbs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cbs)

NOW = datetime.now(timezone.utc)
RECENT = NOW - timedelta(days=1)
OLD = NOW - timedelta(days=60)


def rss(*items):
    body = "".join(
        "<item><title>%s</title><link>%s</link><guid>%s</guid>%s"
        "<description>d</description></item>"
        % (t, link, link, "<pubDate>%s</pubDate>" % pub if pub else "")
        for t, link, pub in items
    )
    return ('<?xml version="1.0"?><rss version="2.0"><channel>%s</channel></rss>' % body).encode()


def rfc822(dt):
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


ATOM = (
    '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">'
    '<entry><title>Atom post</title><link rel="alternate" href="https://blog.example.com/a"/>'
    "<id>urn:post:1</id><updated>%s</updated><summary>s</summary></entry></feed>"
    % RECENT.strftime("%Y-%m-%dT%H:%M:%SZ")
).encode()


class _Resp:
    def __init__(self, body, ctype):
        self._body = body
        self.headers = {"Content-Type": ctype}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def cfg(**feeds):
    return {
        "scan": {
            "competitor_blogs": {"feeds": {name: {"feed_url": url} for name, url in feeds.items()}}
        }
    }


class TestParse(unittest.TestCase):
    def test_rss_items(self):
        items = cbs._parse_rss(rss(("Post", "https://blog.example.com/p", rfc822(RECENT))))
        self.assertEqual(items[0]["title"], "Post")
        self.assertEqual(items[0]["guid"], "https://blog.example.com/p")
        self.assertTrue(items[0]["published_at"].endswith("+00:00"))

    def test_atom_entries(self):
        items = cbs._parse_rss(ATOM)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["url"], "https://blog.example.com/a")
        self.assertEqual(items[0]["guid"], "urn:post:1")
        self.assertIsNotNone(items[0]["published_at"])


class TestFetch(unittest.TestCase):
    def _fetch(self, body, ctype):
        with mock.patch.object(
            cbs.urllib.request, "urlopen", side_effect=lambda req, timeout=15: _Resp(body, ctype)
        ) as m:
            out = cbs._fetch("https://blog.example.com/feed")
        self.ua = m.call_args[0][0].get_header("User-agent")
        return out

    def test_a_feed_without_an_xml_declaration_is_accepted(self):
        body = b'<rss version="2.0"><channel></channel></rss>'
        self.assertEqual(self._fetch(body, "application/rss+xml"), body)

    def test_a_utf8_bom_is_stripped(self):
        body = b'\xef\xbb\xbf<?xml version="1.0"?><rss/>'
        self.assertEqual(self._fetch(body, "application/rss+xml"), body[3:])

    def test_an_html_body_is_named_as_the_reason(self):
        with self.assertRaises(ValueError) as ctx:
            self._fetch(b"<html>blocked</html>", "application/xml")
        self.assertIn("body is not an RSS/Atom feed", str(ctx.exception))

    def test_a_non_xml_content_type_is_named_as_the_reason(self):
        with self.assertRaises(ValueError) as ctx:
            self._fetch(b"<rss/>", "text/html")
        self.assertIn("content-type 'text/html'", str(ctx.exception))

    def test_the_user_agent_names_the_project(self):
        self._fetch(b"<rss/>", "application/rss+xml")
        self.assertTrue(self.ua.startswith("content-engine (+https://"))
        self.assertNotIn("Mozilla", self.ua)


class TestScan(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, cbs, "_fetch", cbs._fetch)
        self.addCleanup(
            setattr, cbs, "_extract_published_from_page", cbs._extract_published_from_page
        )
        cbs._extract_published_from_page = lambda url, timeout=15: None

    def test_one_feed_timing_out_does_not_stop_the_others(self):
        def fetch(url, timeout=15):
            if "one" in url:
                raise socket.timeout("timed out")
            return rss(("Fresh", "https://two.example.com/p", rfc822(RECENT)))

        cbs._fetch = fetch
        out = cbs.scan(
            cfg(one="https://one.example.com/feed", two="https://two.example.com/feed"), 14
        )
        self.assertEqual(out["sources"]["one"]["status"], "failed")
        self.assertIn("timed out", out["sources"]["one"]["error"])
        self.assertEqual(out["sources"]["two"]["fresh_within_window"], 1)

    def test_a_connection_reset_is_a_failed_feed(self):
        def fetch(url, timeout=15):
            raise ConnectionResetError("reset by peer")

        cbs._fetch = fetch
        out = cbs.scan(cfg(one="https://one.example.com/feed"), 14)
        self.assertEqual(out["sources"]["one"]["status"], "failed")

    def test_a_feed_with_no_url_is_a_failed_feed(self):
        out = cbs.scan({"scan": {"competitor_blogs": {"feeds": {"x": {}}}}}, 14)
        self.assertEqual(
            out["sources"]["x"], {"status": "failed", "error": "no feed_url", "feed_url": None}
        )

    def test_an_atom_feed_yields_its_fresh_entry(self):
        cbs._fetch = lambda url, timeout=15: ATOM
        out = cbs.scan(cfg(a="https://blog.example.com/atom"), 14)
        entries = out["sources"]["a"]["entries"]
        self.assertEqual([e["native_id"] for e in entries], ["blog:a:urn:post:1"])

    def test_old_items_are_outside_the_window_and_undated_ones_are_dropped(self):
        cbs._fetch = lambda url, timeout=15: rss(
            ("Old", "https://b.example.com/old", rfc822(OLD)),
            ("Undated", "https://b.example.com/undated", None),
            ("Fresh", "https://b.example.com/fresh", rfc822(RECENT)),
        )
        src = cbs.scan(cfg(b="https://b.example.com/feed"), 14)["sources"]["b"]
        self.assertEqual([e["title"] for e in src["entries"]], ["Fresh"])
        self.assertEqual(src["fetched"], 3)
        self.assertEqual(src["dropped_undated"], 1)

    def test_an_undated_item_recovers_its_date_from_the_page(self):
        cbs._extract_published_from_page = lambda url, timeout=15: RECENT.strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        cbs._fetch = lambda url, timeout=15: rss(("Undated", "https://b.example.com/u", None))
        src = cbs.scan(cfg(b="https://b.example.com/feed"), 14)["sources"]["b"]
        self.assertEqual(len(src["entries"]), 1)
        self.assertEqual(src["dropped_undated"], 0)


RDF = (
    '<?xml version="1.0"?><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
    'xmlns="http://purl.org/rss/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/">'
    '<channel rdf:about="https://blog.example.com/"><title>Blog</title></channel>'
    '<item rdf:about="https://blog.example.com/r1"><title>RDF post</title>'
    "<link>https://blog.example.com/r1</link><dc:date>%s</dc:date></item></rdf:RDF>"
    % RECENT.strftime("%Y-%m-%dT%H:%M:%S+00:00")
).encode()


class TestFeedFormats(unittest.TestCase):
    def test_rdf_feed_items_are_read(self):
        items = cbs._parse_rss(RDF)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["guid"], "https://blog.example.com/r1")
        self.assertIsNotNone(items[0]["published_at"])

    def test_an_rdf_feed_yields_its_fresh_entry(self):
        with mock.patch.object(cbs, "_fetch", lambda url, timeout=15: RDF):
            src = cbs.scan(cfg(r="https://blog.example.com/rdf"), 14)["sources"]["r"]
        self.assertEqual(src["status"], "ok")
        self.assertEqual(src["fresh_within_window"], 1)

    def test_an_unknown_root_is_a_failed_feed(self):
        body = b'<?xml version="1.0"?><opml><body/></opml>'
        with mock.patch.object(cbs, "_fetch", lambda url, timeout=15: body):
            src = cbs.scan(cfg(o="https://blog.example.com/opml"), 14)["sources"]["o"]
        self.assertEqual(src["status"], "failed")
        self.assertIn("unrecognised feed format", src["error"])

    def test_iso_dates_python_39_rejects_are_normalised(self):
        for value in (
            "2026-10-01T00:00:00.12Z",
            "2026-10-01T00:00:00+0000",
            "2026-10-01T00:00:00.1234567+00:00",
        ):
            with self.subTest(value=value):
                dt = cbs._parse_iso(value)
                self.assertIsNotNone(dt)
                self.assertEqual(dt.astimezone(timezone.utc).date().isoformat(), "2026-10-01")

    def test_date_published_wins_over_other_page_dates(self):
        page = (
            b'<meta property="article:published_time" content="2026-09-01T00:00:00Z">'
            b'<time datetime="2026-08-01T00:00:00Z"></time>'
            b'<script>{"datePublished": "2026-10-02T00:00:00Z"}</script>'
        )
        with mock.patch.object(
            cbs.urllib.request,
            "urlopen",
            side_effect=lambda req, timeout=15: _Resp(page, "text/html"),
        ):
            got = cbs._extract_published_from_page("https://blog.example.com/p")
        self.assertTrue(got.startswith("2026-10-02"))


class TestBlogScanEdgeCases(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, cbs, "_fetch", cbs._fetch)
        self.real_extract = cbs._extract_published_from_page
        self.addCleanup(setattr, cbs, "_extract_published_from_page", self.real_extract)
        cbs._extract_published_from_page = lambda url, timeout=15: None

    def _fetch_body(self, body):
        with mock.patch.object(
            cbs.urllib.request,
            "urlopen",
            side_effect=lambda req, timeout=15: _Resp(body, "application/xml"),
        ):
            return cbs._fetch("https://blog.example.com/feed")

    def test_rdf_comments_and_doctype_before_the_root_are_accepted(self):
        for body in (
            b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"/>',
            b"<!-- generated --><!DOCTYPE rss><rss version='2.0'/>",
            b"\n<!-- a -->\n<!-- b -->\n<feed/>",
        ):
            with self.subTest(body=body):
                self.assertIsNotNone(self._fetch_body(body))

    def test_the_page_date_fallback_fetches_http_links_only(self):
        with mock.patch.object(cbs.urllib.request, "urlopen") as m:
            self.assertIsNone(self.real_extract("file:///etc/hosts"))
            self.assertIsNone(self.real_extract("ftp://example.com/x"))
            m.assert_not_called()

    def test_a_future_dated_item_is_dropped(self):
        future = NOW + timedelta(days=30)
        cbs._fetch = lambda url, timeout=15: rss(
            ("Later", "https://b.example.com/f", rfc822(future)),
            ("Now", "https://b.example.com/n", rfc822(RECENT)),
        )
        src = cbs.scan(cfg(b="https://b.example.com/feed"), 14)["sources"]["b"]
        self.assertEqual([e["title"] for e in src["entries"]], ["Now"])
        self.assertEqual(src["dropped_future"], 1)

    def test_an_item_exactly_at_the_window_start_is_kept(self):
        fixed = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)

        class FixedDT(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed

        edge = fixed - timedelta(days=14)
        cbs._fetch = lambda url, timeout=15: rss(("Edge", "https://b.example.com/e", rfc822(edge)))
        with mock.patch.object(cbs, "datetime", FixedDT):
            src = cbs.scan(cfg(b="https://b.example.com/feed"), 14)["sources"]["b"]
        self.assertEqual(src["fresh_within_window"], 1)

    def test_atom_published_wins_over_updated(self):
        body = (
            b'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><title>A</title>'
            b"<id>urn:a</id><published>2026-10-01T00:00:00Z</published>"
            b"<updated>2026-10-05T00:00:00Z</updated></entry></feed>"
        )
        self.assertTrue(cbs._parse_rss(body)[0]["published_at"].startswith("2026-10-01"))

    def test_malformed_xml_is_a_failed_feed(self):
        cbs._fetch = lambda url, timeout=15: b'<?xml version="1.0"?><rss><channel>'
        src = cbs.scan(cfg(b="https://b.example.com/feed"), 14)["sources"]["b"]
        self.assertEqual(src["status"], "failed")


class TestBlogScanDates(unittest.TestCase):
    FIXED = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)

    def setUp(self):
        self.addCleanup(setattr, cbs, "_fetch", cbs._fetch)
        self.real_extract = cbs._extract_published_from_page
        self.addCleanup(setattr, cbs, "_extract_published_from_page", self.real_extract)
        cbs._extract_published_from_page = lambda url, timeout=15: None

    def _scan(self):
        fixed = self.FIXED

        class FixedDT(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed

        with mock.patch.object(cbs, "datetime", FixedDT):
            return cbs.scan(cfg(b="https://b.example.com/feed"), 14)["sources"]["b"]

    def test_a_minute_ahead_is_kept_and_a_day_ahead_is_dropped(self):
        cbs._fetch = lambda url, timeout=15: rss(
            ("Skewed", "https://b.example.com/s", rfc822(self.FIXED + timedelta(seconds=60))),
            ("Tomorrow", "https://b.example.com/t", rfc822(self.FIXED + timedelta(days=1))),
        )
        src = self._scan()
        self.assertEqual([e["title"] for e in src["entries"]], ["Skewed"])
        self.assertEqual(src["dropped_future"], 1)

    def test_a_future_date_from_the_page_is_dropped(self):
        later = (self.FIXED + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        cbs._extract_published_from_page = lambda url, timeout=15: later
        cbs._fetch = lambda url, timeout=15: rss(("Undated", "https://b.example.com/u", None))
        src = self._scan()
        self.assertEqual(src["entries"], [])
        self.assertEqual(src["dropped_future"], 1)

    def test_the_page_date_fallback_refuses_data_and_javascript_links(self):
        with mock.patch.object(cbs.urllib.request, "urlopen") as m:
            self.assertIsNone(self.real_extract("data:text/html,<time datetime='2026-10-01'>"))
            self.assertIsNone(self.real_extract("javascript:alert(1)"))
            m.assert_not_called()


class TestBlogScanConfig(unittest.TestCase):
    def test_a_config_that_is_not_a_mapping_is_a_message(self):
        import subprocess
        import tempfile

        d = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, d, True)
        script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "competitor-blog-scan.py"
        )
        for text, message in (
            ("- a\n- b\n", "is empty or not a YAML mapping"),
            ("", "is empty or not a YAML mapping"),
            ("# only a comment\n", "is empty or not a YAML mapping"),
            ("scan: [1]\n", "`scan` in"),
            ("scan:\n  competitor_blogs:\n    feeds: {}\n", "competitor_blogs.feeds"),
            ("scan:\n  competitor_blogs:\n    lookback_days: 7\n", "competitor_blogs.feeds"),
            ("scan: {}\n", "competitor_blogs.feeds"),
        ):
            with self.subTest(text=text):
                cfg = os.path.join(d, "c.yaml")
                with open(cfg, "w") as f:
                    f.write(text)
                r = subprocess.run(
                    [sys.executable, script, "--config", cfg], capture_output=True, text=True, cwd=d
                )
                self.assertNotEqual(r.returncode, 0)
                self.assertIn(message, r.stderr)
                self.assertNotIn("Traceback", r.stderr)
                self.assertNotIn("fresh entries", r.stdout)


class TestBlogScanRssDates(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, cbs, "_fetch", cbs._fetch)
        self.addCleanup(
            setattr, cbs, "_extract_published_from_page", cbs._extract_published_from_page
        )
        cbs._extract_published_from_page = lambda url, timeout=15: None

    def test_an_rss_item_dated_only_with_dc_date_keeps_its_date(self):
        raw = (
            '<?xml version="1.0"?><rss version="2.0" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/"><channel>'
            "<item><title>DC</title><link>https://blog.example.com/dc</link>"
            "<dc:date>%s</dc:date></item></channel></rss>" % RECENT.strftime("%Y-%m-%dT%H:%M:%SZ")
        ).encode()
        items = cbs._parse_rss(raw)
        self.assertTrue(items[0]["published_at"].startswith(RECENT.strftime("%Y-%m-%dT%H:%M")))
        cbs._fetch = lambda url, timeout=15: raw
        src = cbs.scan(cfg(d="https://blog.example.com/feed"), 14)["sources"]["d"]
        self.assertEqual([e["title"] for e in src["entries"]], ["DC"])

    def test_a_feed_given_as_a_string_fails_alone(self):
        cbs._fetch = lambda url, timeout=15: rss(
            ("Fresh", "https://two.example.com/p", rfc822(RECENT))
        )
        conf = {
            "scan": {
                "competitor_blogs": {
                    "feeds": {
                        "x": "https://one.example.com/feed",
                        "two": {"feed_url": "https://two.example.com/feed"},
                    }
                }
            }
        }
        out = cbs.scan(conf, 14)["sources"]
        self.assertEqual(out["x"]["status"], "failed")
        self.assertIn("feed must be a mapping with feed_url", out["x"]["error"])
        self.assertEqual([e["title"] for e in out["two"]["entries"]], ["Fresh"])

    def test_the_future_slack_is_five_minutes(self):
        self.assertEqual(cbs.FUTURE_SLACK_SECONDS, 300)
        inside = NOW + timedelta(seconds=240)
        outside = NOW + timedelta(seconds=420)
        cbs._fetch = lambda url, timeout=15: rss(
            ("Inside", "https://b.example.com/i", rfc822(inside)),
            ("Outside", "https://b.example.com/o", rfc822(outside)),
        )
        src = cbs.scan(cfg(b="https://b.example.com/feed"), 14)["sources"]["b"]
        self.assertEqual([e["title"] for e in src["entries"]], ["Inside"])
        self.assertEqual(src["dropped_future"], 1)


class TestBlogScanDateFallback(unittest.TestCase):
    def _item(self, pub, dc):
        return (
            '<?xml version="1.0"?><rss version="2.0" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/"><channel>'
            "<item><title>T</title><link>https://blog.example.com/t</link>"
            "<pubDate>%s</pubDate><dc:date>%s</dc:date></item></channel></rss>" % (pub, dc)
        ).encode()

    def test_an_unparseable_pubdate_falls_back_to_dc_date(self):
        items = cbs._parse_rss(self._item("not a date", "2026-09-01T10:00:00Z"))
        self.assertEqual(items[0]["published_at"], "2026-09-01T10:00:00+00:00")

    def test_a_parseable_pubdate_wins_over_dc_date(self):
        items = cbs._parse_rss(
            self._item("Tue, 29 Sep 2026 08:00:00 +0000", "2026-09-01T10:00:00Z")
        )
        self.assertEqual(items[0]["published_at"], "2026-09-29T08:00:00+00:00")


class TestImportedBlogScanOutput(unittest.TestCase):
    def test_main_writes_in_the_caller_not_the_engine(self):
        import contextlib
        import io
        import json
        import shutil
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp) / "engine"
            caller = Path(tmp) / "caller"
            script = engine / "packages/content-engine/competitor-blog-scan.py"
            script.parent.mkdir(parents=True)
            caller.mkdir()
            shutil.copyfile(cbs.__file__, script)
            spec = importlib.util.spec_from_file_location("imported_blog_scan", script)
            imported = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(imported)
            config = caller / "config.yaml"
            config.write_text(
                "scan:\n  competitor_blogs:\n    feeds:\n      a:\n"
                "        feed_url: https://a.example.com/feed\n"
            )
            previous = os.getcwd()
            try:
                os.chdir(caller)
                with (
                    mock.patch.object(imported, "_fetch", return_value=rss()),
                    mock.patch.object(sys, "argv", [str(script), "--config", str(config)]),
                    contextlib.redirect_stdout(io.StringIO()),
                    contextlib.redirect_stderr(io.StringIO()),
                ):
                    imported.main()
            finally:
                os.chdir(previous)
            outputs = list((caller / "working/content-engine/signals").glob("*.json"))
            self.assertEqual(len(outputs), 1)
            self.assertEqual(json.loads(outputs[0].read_text())["sources"]["a"]["status"], "ok")
            self.assertFalse((engine / "working").exists())


class TestBlogScanExit(unittest.TestCase):
    def run_main(self, config_text, fetch):
        import contextlib
        import io
        import tempfile

        d = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, d, True)
        cfg = os.path.join(d, "c.yaml")
        with open(cfg, "w") as f:
            f.write(config_text)
        err = io.StringIO()
        code = 0
        previous = os.getcwd()
        self.addCleanup(os.chdir, previous)
        os.chdir(d)
        with (
            mock.patch.object(cbs, "_fetch", fetch),
            mock.patch.object(sys, "argv", ["competitor-blog-scan.py", "--config", cfg]),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(err),
        ):
            try:
                cbs.main()
            except SystemExit as e:
                code = e.code if isinstance(e.code, int) else 1
                err.write(str(e.code))
        return code, err.getvalue()

    FEEDS = (
        "scan:\n  competitor_blogs:\n%s    feeds:\n      a:\n"
        "        feed_url: https://a.example.com/feed\n"
    )

    def test_every_feed_failing_exits_non_zero(self):
        def fetch(url, timeout=15):
            raise OSError("connection refused")

        code, err = self.run_main(self.FEEDS % "", fetch)
        self.assertEqual(code, 1)
        self.assertIn("Every competitor blog feed failed", err)

    def test_lookback_days_must_be_a_whole_number(self):
        for bad in ('"14"', "0", "-3", "true", "1.5"):
            with self.subTest(bad=bad):
                code, err = self.run_main(self.FEEDS % ("    lookback_days: %s\n" % bad), None)
                self.assertNotEqual(code, 0)
                self.assertIn("lookback_days", err)
                self.assertNotIn("Traceback", err)


class TestBlogScanPartialExit(TestBlogScanExit):
    FEEDS2 = (
        "scan:\n  competitor_blogs:\n%s    feeds:\n"
        "      a:\n        feed_url: https://a.example.com/feed\n"
        "      b:\n        feed_url: https://b.example.com/feed\n"
    )

    def test_some_feeds_failing_exits_zero(self):
        def fetch(url, timeout=15):
            if "a.example.com" in url:
                raise OSError("connection refused")
            return (
                b'<?xml version="1.0"?><rss version="2.0"><channel><title>b</title></channel></rss>'
            )

        code, err = self.run_main(self.FEEDS2 % "", fetch)
        self.assertEqual(code, 0, err)

    def test_whole_numbers_of_days_are_accepted(self):
        def fetch(url, timeout=15):
            return b'<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>'

        for good in ("1", "14"):
            with self.subTest(good=good):
                code, err = self.run_main(self.FEEDS % ("    lookback_days: %s\n" % good), fetch)
                self.assertEqual(code, 0, err)


if __name__ == "__main__":
    unittest.main()
