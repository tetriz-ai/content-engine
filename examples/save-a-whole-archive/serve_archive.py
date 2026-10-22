"""Serve a sample Substack archive and a sample blog sitemap on 127.0.0.1, and save both
with archive_fetch.py.

The publication has three posts, one of them for paid subscribers. The sitemap lists a
/guides/ folder with two category folders, the folder page of one of them, and a page
outside /guides/. No request leaves the machine.
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PARAGRAPH = (
    "Every incident I write down what I expected before I read the logs. "
    "It keeps the postmortem honest when the cause turns up. "
) * 5

POSTS = [
    (
        "what-our-test-quarantine-taught-us",
        "What our test quarantine taught us",
        "2026-09-28",
        "everyone",
    ),
    (
        "members-only-our-ci-bill",
        "Members only: our CI bill, line by line",
        "2026-07-02",
        "only_paid",
    ),
    ("why-i-write-postmortems", "Why I write postmortems", "2026-01-15", "everyone"),
]


def archive(base, offset):
    page = POSTS[offset:]
    return [
        {
            "slug": slug,
            "title": title,
            "post_date": date + "T08:00:00.000Z",
            "audience": audience,
            "canonical_url": "%s/p/%s" % (base, slug),
            "type": "newsletter",
        }
        for slug, title, date, audience in page[:2]
    ]


def post(base, slug):
    for s, title, date, audience in POSTS:
        if s == slug:
            body = "<p>A short teaser.</p>" if audience != "everyone" else "<p>%s</p>" % PARAGRAPH
            return {
                "slug": s,
                "title": title,
                "post_date": date + "T08:00:00.000Z",
                "audience": audience,
                "canonical_url": "%s/p/%s" % (base, s),
                "body_html": body,
            }
    return None


SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>{base}/guides/ci-reliability</loc><lastmod>2026-09-01</lastmod></url>
<url><loc>{base}/guides/ci-reliability/flaky-test-quarantine-results</loc><lastmod>2026-09-20</lastmod></url>
<url><loc>{base}/guides/test-tooling/test-runner-checklist</loc><lastmod>2026-08-11</lastmod></url>
<url><loc>{base}/about</loc></url>
</urlset>
"""

GUIDE = """<html><head><title>{title} | Example Guides</title></head><body>
<nav>Home Guides Reliability Tooling</nav>
<article><h1>{title}</h1>
<p>{text}</p>
<h2>{section}</h2>
<ul><li>{one}</li><li>{two}</li></ul>
</article>
<footer>Example Guides, all rights reserved</footer></body></html>"""

GUIDES = {
    "/guides/ci-reliability/flaky-test-quarantine-results": GUIDE.format(
        title="Flaky-test quarantine results",
        text="What a month of quarantining flaky tests did, and the three numbers we watched. " * 3,
        section="What changed",
        one="Re-runs per day",
        two="Time to a green build",
    ),
    "/guides/test-tooling/test-runner-checklist": GUIDE.format(
        title="Test runner checklist",
        text="Five things to check before you switch test runners, in the order to check them. "
        * 3,
        section="The checklist",
        one="Parallel runs",
        two="Retry rules",
    ),
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        base = self.server.base
        path, _, query = self.path.partition("?")
        body, ctype = None, "application/json"
        if path == "/api/v1/archive":
            offset = int(dict(p.split("=") for p in query.split("&")).get("offset", 0))
            body = json.dumps(archive(base, offset))
        elif path.startswith("/api/v1/posts/"):
            found = post(base, path.rsplit("/", 1)[1])
            body = json.dumps(found) if found else None
        elif path == "/sitemap.xml":
            body, ctype = SITEMAP.format(base=base), "application/xml"
        elif path in GUIDES:
            body, ctype = GUIDES[path], "text/html"
        if body is None:
            self.send_error(404)
            return
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.base = "http://127.0.0.1:%d" % server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    env = dict(os.environ, NO_PROXY="127.0.0.1", no_proxy="127.0.0.1")
    with tempfile.TemporaryDirectory() as d:
        profile = os.path.join(d, "profile.yaml")
        with open(profile, "w") as f:
            f.write(
                "archive_dir: %s/archive\n"
                "archive_sources:\n"
                "  - substack: %s\n"
                "    min_gap_seconds: 0\n"
                "  - sitemap: %s/sitemap.xml\n"
                "    path_prefix: /guides/\n"
                "    min_gap_seconds: 0\n"
                "content_types: [postmortem, checklist, other]\n" % (d, server.base, server.base)
            )
        for script, args in (("archive_fetch.py", []), ("archive_tag.py", ["--list"])):
            run = subprocess.run(
                [sys.executable, "packages/content-engine/" + script, "--profile", profile, *args],
                capture_output=True,
                text=True,
                env=env,
                check=True,
            )
            print(run.stdout.replace(server.base, "<site>").replace(d, "<tmp>"), end="")
        for name in sorted(os.listdir(os.path.join(d, "archive"))):
            if not name.startswith("."):
                print(name)
    server.shutdown()


if __name__ == "__main__":
    main()
