"""List matching Product Hunt launches with scanner-core's scan_ph and fetch_details.

urlopen is replaced by a stub that plays Product Hunt's GraphQL API from canned
replies. One topic answers with HTTP 502, so it shows up in `failures` while the
other topic's launches still come back. Any other URL raises, so no request
leaves the machine and no token is needed.
"""

import io
import json
import urllib.error
import urllib.request

import scanner_core as sc

LAUNCHES = {
    "developer-tools": [
        {
            "id": "11",
            "name": "Example Launch A",
            "tagline": "Finds the flaky test in your CI",
            "votes": 120,
            "topics": ["Developer Tools"],
        },
        {
            "id": "12",
            "name": "Example Launch B",
            "tagline": "Release notes from your commits",
            "votes": 45,
            "topics": ["Developer Tools"],
        },
        {
            "id": "13",
            "name": "Example Launch C",
            "tagline": "Water reminders for houseplants",
            "votes": 300,
            "topics": ["Home"],
        },
    ],
}
DETAILS = {
    "11": {
        "votes": [{"username": "janedoe"}, {"username": "maker_one"}],
        "comments": [{"username": "johndoe", "body": "We lose an hour a day to re-runs."}],
    },
    "12": {"votes": [{"username": "johndoe"}], "comments": []},
}


def node(launch):
    return {
        "id": launch["id"],
        "name": launch["name"],
        "tagline": launch["tagline"],
        "description": "",
        "url": "https://www.producthunt.com/posts/%s" % launch["id"],
        "website": "https://example.com",
        "votesCount": launch["votes"],
        "commentsCount": 1,
        "createdAt": "2026-10-07T08:00:00Z",
        "topics": {"edges": [{"node": {"name": t, "slug": t.lower()}} for t in launch["topics"]]},
        "makers": [
            {
                "id": "m",
                "name": "Maker",
                "username": "maker_one",
                "headline": None,
                "url": None,
                "twitterUsername": None,
                "websiteUrl": None,
            }
        ],
    }


def user(name):
    return {"user": {"id": name, "name": name, "username": name, "url": None}}


class Reply(io.BytesIO):
    def __init__(self, payload):
        super().__init__(json.dumps(payload).encode())
        self.headers = {"Content-Type": "application/json"}


def fake_urlopen(req, timeout=None):
    if req.full_url != sc.PH_API:
        raise urllib.error.URLError("no canned reply for %s" % req.full_url)
    variables = json.loads(req.data)["variables"]
    if "topic" in variables:
        if variables["topic"] not in LAUNCHES:
            raise urllib.error.HTTPError(req.full_url, 502, "Bad Gateway", {}, None)
        edges = [{"node": node(x)} for x in LAUNCHES[variables["topic"]]]
        posts = {"pageInfo": {"hasNextPage": False, "endCursor": None}, "edges": edges}
        return Reply({"data": {"posts": posts}})
    d = DETAILS[variables["id"]]
    votes = {"edges": [{"node": user(v["username"])} for v in d["votes"]]}
    comments = {
        "edges": [
            {"node": dict(user(c["username"]), body=c["body"], votesCount=2)} for c in d["comments"]
        ]
    }
    return Reply({"data": {"post": {"id": variables["id"], "votes": votes, "comments": comments}}})


def main():
    urllib.request.urlopen = fake_urlopen
    sc.time.sleep = lambda seconds: None
    cfg = {
        "ph": {
            "topics": ["developer-tools", "testing"],
            "max_pages": 1,
            "posts_per_page": 20,
            "require_fit": True,
            "min_votes": 10,
            "keywords": ["flaky test"],
            "fit_topics": ["developer-tools"],
            "detail_fetch_top": 5,
            "voters_limit": 20,
            "comments_limit": 20,
        }
    }
    failures = []
    launches = sc.scan_ph(cfg, "token-not-needed", "2026-10-07T07:00:00Z", failures)
    sc.fetch_details(cfg, "token-not-needed", launches, failures)
    for c in launches:
        why = c["matched_keywords"] or ["topic: " + ", ".join(c["fit_topics_matched"])]
        print("%-6s %-16s %3d votes  %s" % (c["id"], c["name"], c["votes_count"], "; ".join(why)))
        for u in c["top_voters"]:
            print("         voter      @%s" % u["username"])
        for u in c["top_commenters"]:
            print("         commenter  @%s: %s" % (u["username"], u["comment_excerpt"]))
    for f in failures:
        print("failed: %s %s: %s" % (f["platform"], f["request"], f["error"]))


if __name__ == "__main__":
    main()
