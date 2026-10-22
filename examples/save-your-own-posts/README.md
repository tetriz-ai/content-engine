Saves the posts in a sample blog feed as a writer archive, the folder the writer learns your voice from. The feed is read from a local file, so no request leaves the machine. One post arrives whole and is saved as Markdown. The other is a summary only, as a paid post would be, and is flagged.

```sh
examples/save-your-own-posts/run.sh
```

```text
  [warn] 2026-09-25-members-only-our-ci-budget.md: the feed carries only a summary of this post. Paste the full post into <tmp>/archive for a better voice example.
  file://examples/save-your-own-posts/feed.xml: 2 posts, 2 new, 0 already saved
  tag index: 2 posts, 2 without a content type; run archive_tag.py --profile <tmp>/profile.yaml
2 new, 0 already saved, 0 source(s) failed -> <tmp>/archive
2026-09-25-members-only-our-ci-budget.md
2026-09-29-why-i-stopped-re-running-red-builds.md

# Why I stopped re-running red builds

Source: https://blog.example.com/stopped-re-running-red-builds (published 2026-09-29)

For a year our team treated a red build as a suggestion. Someone would hit re-run, it would go green, and we would move on.

It felt fast. It was not: every re-run hid a test we had stopped trusting.

## What changed

We started tagging a test as flaky the second time it failed and passed on a re-run, and we kept a list on the team wiki.

- The list was short.
- The same five tests were on it every week.

Fixing those five did more for trust in CI than any dashboard. Nobody had to be told to stop re-running: once a red build meant something again, people started reading it.
```
