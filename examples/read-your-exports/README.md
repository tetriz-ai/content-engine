Saves your posts from the two data exports, the zip files Medium and LinkedIn email you from your account settings. The sample exports are small folders made in the layout those exports are documented to have, and the script also takes the zip itself. Medium's drafts and responses are left out, and so is a LinkedIn share with no text of its own.

```sh
examples/read-your-exports/run.sh
```

```text
  examples/read-your-exports/medium-export: skipped 1 draft(s), 1 response(s)
  examples/read-your-exports/medium-export: 1 posts, 1 new, 0 already saved
  examples/read-your-exports/linkedin-export: skipped 1 rows with no text
  examples/read-your-exports/linkedin-export: 1 posts, 1 new, 0 already saved
  tag index: 2 posts, 2 without a content type; run archive_tag.py --profile <tmp>/profile.yaml
2 new, 0 already saved, 0 source(s) failed -> <tmp>/archive
2025-11-03-how-we-cut-ci-time-in-half.md
2026-03-10-our-build-went-from-22-minutes-to-9.md

# How we cut CI time in half

Source: https://medium.com/@example-author/how-we-cut-ci-time-in-half-1a2b3c4d5e6f (published 2025-11-03)

We started by measuring where the minutes went.

#### Cache first

Most of the time was spent downloading the same dependencies on every run.

# Our build went from 22 minutes to 9 …

Source: https://social.example.com/posts/example-author-1 (published 2026-03-10)

Our build went from 22 minutes to 9 this quarter.

The biggest win was the boring one: a dependency cache.
```
