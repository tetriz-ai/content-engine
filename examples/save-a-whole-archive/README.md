Saves a whole Substack archive and one folder of a blog's sitemap as a writer archive. Both are served on 127.0.0.1, so no request leaves the machine. The Substack posts come from the archive list, each read whole, and the post for paid subscribers is flagged. The sitemap pages come from `/guides/` only, each with the category its URL folder names. The folder page of `ci-reliability` and the page outside `/guides/` are not saved.

```sh
examples/save-a-whole-archive/run.sh
```

```text
  [warn] 2026-07-02-members-only-our-ci-bill-line-by-line.md is for paid subscribers, so only its preview was saved. Paste the full post into <tmp>/archive for a better voice example.
  <site> (archive): 3 posts, 3 new, 0 already saved
  [skip] 1 folder page(s) that list other pages
  <site>/sitemap.xml: 2 pages under /guides/
  <site>/sitemap.xml: 2 posts, 2 new, 0 already saved
  tag index: 5 posts, 5 without a content type; run archive_tag.py --profile <tmp>/profile.yaml
5 new, 0 already saved, 0 source(s) failed -> <tmp>/archive
posts: 5, untagged: 5
categories: ci-reliability (1), test-tooling (1)
content types: none
2026-01-15-why-i-write-postmortems.md
2026-07-02-members-only-our-ci-bill-line-by-line.md
2026-09-28-what-our-test-quarantine-taught-us.md
ci-reliability-flaky-test-quarantine-results.md
test-tooling-test-runner-checklist.md
```
