"""Serve a sample competitor blog feed on 127.0.0.1 and read it with competitor-blog-scan.py.

The feed has three posts: one dated in the feed, one whose date is only on its own page,
and one with no date anywhere. No request leaves the machine.
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FEED = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>Example blog</title>
<item><title>Why we quarantine flaky tests</title><link>{base}/posts/quarantine</link>
<guid>urn:example:1</guid><pubDate>Thu, 01 Oct 2026 09:00:00 +0000</pubDate></item>
<item><title>Measuring CI re-runs</title><link>{base}/posts/reruns</link>
<guid>urn:example:2</guid></item>
<item><title>An undated note</title><link>{base}/posts/undated</link>
<guid>urn:example:3</guid></item>
</channel></rss>
"""
PAGES = {
    "/posts/reruns": '<script type="application/ld+json">'
    '{"datePublished": "2026-09-30T08:00:00Z"}</script>',
    "/posts/undated": "<p>No date here.</p>",
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/feed.xml":
            body, ctype = FEED.format(base=self.server.base).encode(), "application/rss+xml"
        elif self.path in PAGES:
            body, ctype = PAGES[self.path].encode(), "text/html"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.base = "http://127.0.0.1:%d" % server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with tempfile.TemporaryDirectory() as d:
        config = os.path.join(d, "config.yaml")
        with open(config, "w") as f:
            f.write(
                "scan:\n  competitor_blogs:\n    lookback_days: 36500\n    feeds:\n"
                "      example_blog:\n        feed_url: %s/feed.xml\n" % server.base
            )
        env = dict(os.environ, NO_PROXY="127.0.0.1", no_proxy="127.0.0.1")
        run = subprocess.run(
            [sys.executable, "packages/content-engine/competitor-blog-scan.py", "--config", config],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
    server.shutdown()
    out_path = run.stdout.strip().splitlines()[-1].split(" -> ")[-1]
    with open(out_path) as f:
        src = json.load(f)["sources"]["example_blog"]
    print(
        "status: %s, %d in the feed, %d kept, %d dropped with no date"
        % (src["status"], src["fetched"], src["fresh_within_window"], src["dropped_undated"])
    )
    for e in src["entries"]:
        print("%s  %s  %s" % (e["published_at"], e["native_id"], e["title"]))


if __name__ == "__main__":
    main()
