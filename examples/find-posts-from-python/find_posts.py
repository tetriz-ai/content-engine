"""Call scanner-core's scan_hn and scan_reddit from Python, with canned replies.

urlopen and the budgeted Reddit transport are replaced by stubs that answer
from the data below, fail one feed with HTTP 500, and raise on any other URL,
so no request leaves the machine and no network worker is started.
"""

import io
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import scanner_core as sc

HN = {
    "hits": [
        {
            "objectID": "101",
            "title": "Show HN: A flaky test detector for CI",
            "points": 48,
            "num_comments": 12,
            "_tags": ["story", "show_hn"],
            "author": "jdoe",
            "created_at": "2026-10-05T09:00:00Z",
        },
        {
            "objectID": "102",
            "title": "Ask HN: Too few points to count",
            "points": 1,
            "_tags": ["story", "ask_hn"],
            "created_at": "2026-10-05T10:00:00Z",
        },
    ]
}
REDDIT_NEW = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><id>t3_aaa</id><title>Our CI pipeline reliability is getting worse</title>
<updated>2026-10-05T08:00:00+00:00</updated><content>Every third build is red.</content>
<link href="https://www.reddit.com/r/ExperiencedDevs/comments/aaa/"/></entry>
<entry><id>t3_bbb</id><title>What do you eat for lunch</title>
<updated>2026-10-05T08:30:00+00:00</updated><content>Nothing about tests.</content>
<link href="https://www.reddit.com/r/ExperiencedDevs/comments/bbb/"/></entry>
</feed>"""
EMPTY_FEED = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'


class Reply(io.BytesIO):
    def __init__(self, body, ctype):
        super().__init__(body.encode())
        self.headers = {"Content-Type": ctype}


def fake_urlopen(req, timeout=None):
    url = req.full_url
    if url.startswith("https://hn.algolia.com/api/v1/search?"):
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["query"][0]
        return Reply(json.dumps(HN if "flaky" in query else {"hits": []}), "application/json")
    if url == "https://www.reddit.com/r/devops/hot/.rss?limit=%d" % sc.REDDIT_FEED_LIMIT:
        raise urllib.error.HTTPError(url, 500, "Internal Server Error", {}, None)
    if url == "https://www.reddit.com/r/ExperiencedDevs/new/.rss?limit=%d" % sc.REDDIT_FEED_LIMIT:
        return Reply(REDDIT_NEW, "application/atom+xml")
    if url.startswith("https://www.reddit.com/r/"):
        return Reply(EMPTY_FEED, "application/atom+xml")
    raise urllib.error.URLError("no canned reply for %s" % url)


def main():
    urllib.request.urlopen = fake_urlopen

    def fake_reddit_fetch(url):
        reply = fake_urlopen(urllib.request.Request(url))
        return reply.read(), reply.headers["Content-Type"]

    sc._reddit_fetch_once = fake_reddit_fetch
    sc.time.sleep = lambda seconds: None
    cfg = {
        "hn": {"tags": ["story", "show_hn", "ask_hn"], "min_points": 3},
        "subreddits": [{"name": "ExperiencedDevs"}, {"name": "devops"}],
        "reddit_min_gap_seconds": 0,
        "keywords": {"precise": ["flaky test", "ci pipeline reliability"]},
    }
    since = int(datetime(2026, 10, 1, tzinfo=timezone.utc).timestamp())
    failures = []
    posts = sc.scan_hn(cfg, since, failures) + sc.scan_reddit(cfg, since, failures)
    for post in posts:
        words = ", ".join(kw for kw, layer in post["matched_keywords"])
        print("%-16s %s  [%s]" % (post["id"], post["title"], words))
    for f in failures:
        print("failed: %s %s: %s" % (f["platform"], f["request"], f["error"]))


if __name__ == "__main__":
    main()
