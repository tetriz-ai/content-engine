A writer of your own that honours the writer contract: it takes `--theme-doc`, `--format` and `--out`, refuses a theme with no signal (a row or list item under `## Signals` with a real URL) or with two `## Signals` sections, and writes a Markdown draft with `status: draft` frontmatter. This one only outlines the theme's evidence. Point `write.<format>.command` in `config.yaml` at a program like it to use your own writer.

```sh
examples/plug-in-your-own-writer/run.sh
```

```text
Outline written -> working/examples/outline.md
---
status: draft
format: blog
source_theme_doc: packages/content-engine/examples/theme-example-ci-flakiness.md
generated_at: <time>
drafted_by: outline-writer
---

# Flaky Tests Are a Quiet, Measurable Tax on CI Throughput

1. Open with: Show HN: We cut our flaky-test rate by tagging non-deterministic failures automatically
2. Open with: Tests failing randomly again — anyone else re-running CI 3x a day just to get a green build?
3. Open with: Flaky Tests Cost More Than You Think: A 2026 Survey of 400 Engineering Teams
```
