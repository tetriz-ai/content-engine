# Glossary

| Term | Meaning |
|---|---|
| Signal | One post from a source, such as a Hacker News story, saved as evidence. |
| Signal bank | `context-library/content-signal-bank.jsonl`, every signal ever found, one JSON object per line. |
| Spent | A signal whose `theme_id` is set because a theme used it. A spent signal is never grouped again. |
| Theme | A group of signals about one thing, written up as a theme doc in `docs/content-themes/`. |
| Coverage tier | STRONG or THIN, a count of a theme's evidence. With the example config, STRONG is 3 or more posts from 2 or more sources, and THIN is anything less. |
| Author's take | A `## Author's take` section in a theme doc: your own opinion, which the draft argues as yours. It comes from a reply on the Slack card or is written by hand. |
| Requested changes | A `## Requested changes` section: what the approver asked to change, from replies on a ✏️ approval. A requested change overrides the format settings. |
| Content type | The kind of piece, such as a postmortem, from the writer profile's `content_types`. Each saved post and each theme gets one. |
| Category | The folder in a post's URL below the sitemap's `path_prefix`, such as `ci-reliability`. |
| Voice example | One of your past posts, put in the drafting prompt so the draft copies your style. Posts of the theme's content type come first. |
| Dry run | `/content-engine --dry-run`: the whole run with every side effect replaced by a preview file under `working/`, and nothing sent to Slack. |
