Serves a sample blog feed on 127.0.0.1 and reads it with the competitor blog scanner, so no request leaves the machine. One post is dated in the feed, one only on its own page, and one nowhere. The undated one is dropped, never assumed fresh.

```sh
examples/read-a-competitor-feed/run.sh
```

```text
status: ok, 3 in the feed, 2 kept, 1 dropped with no date
2026-10-01T09:00:00+00:00  blog:example_blog:urn:example:1  Why we quarantine flaky tests
2026-09-30T08:00:00+00:00  blog:example_blog:urn:example:2  Measuring CI re-runs
```
