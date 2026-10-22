# Examples

| You want | Example |
|---|---|
| Signal counts per source and theme counts per status | [count-signals-and-themes](count-signals-and-themes/) |
| A relevance score without an API key | [score-a-theme-without-an-api-key](score-a-theme-without-an-api-key/) |
| The exact prompt a draft will get | [preview-a-drafting-prompt](preview-a-drafting-prompt/) |
| A draft without an API key | [draft-without-an-api-key](draft-without-an-api-key/) |
| Your own writer in place of the bundled one | [plug-in-your-own-writer](plug-in-your-own-writer/) |
| Hacker News and Reddit posts from your own Python code | [find-posts-from-python](find-posts-from-python/) |
| Matching Product Hunt launches from your own Python code | [list-matching-product-hunt-launches](list-matching-product-hunt-launches/) |
| A competitor blog feed read end to end | [read-a-competitor-feed](read-a-competitor-feed/) |
| Your own published posts saved as voice examples | [save-your-own-posts](save-your-own-posts/) |
| Your posts from a Medium or LinkedIn data export | [read-your-exports](read-your-exports/) |
| Your saved posts tagged by type, and the voice examples a theme gets | [tag-your-archive](tag-your-archive/) |
| A whole Substack archive and one folder of a blog's sitemap | [save-a-whole-archive](save-a-whole-archive/) |

Run them all with `scripts/run-examples.sh` from the repo root. They use the bundled sample files, canned replies, and a feed, an archive and a sitemap served on 127.0.0.1, so they need no key, no account and no network. The runner rewrites each `generated_at:` value to `<time>` before comparing output.
