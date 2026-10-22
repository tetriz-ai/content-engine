# content-engine

## What this is

`/content-engine` is a Claude Code and Codex workflow that scans Hacker News, Reddit, news and competitor
blogs, groups posts into evidence-graded themes, and drafts only the themes a person approved.
It never publishes, never scrapes LinkedIn, and never drafts a theme nobody approved.

## Layout

- `SKILL.md`, `skills/blog/`, `skills/editorial-draft/`: native host pipeline and editorial resources.
- `scripts/install-skills.py`, `scripts/resolve-context.py`: caller-safe installation and paths.
- `.claude/commands/content-engine.md`: the command. Every mode, step and file it writes.
- `packages/content-engine/`: config templates, `rules.md`, sample files in `examples/`, and six
  scripts: `write_reference.py`, `relevance_scorer.py`, `report.py`, `competitor-blog-scan.py`,
  `archive_fetch.py` and `archive_tag.py`.
- `packages/scanner-core/scanner_core.py`: the HN, Reddit, Product Hunt and X fetchers.
- `packages/*/tests/`: unittest suites. `_guard.py` in each is imported first by every test.
- `examples/`: runnable examples and their index. `scripts/run-examples.sh` runs them.

## Commands

Python 3.9 is the floor. Tests and examples run in `.venv` (CI tests on 3.9, 3.13 and 3.14):

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -r packages/scanner-core/requirements.txt
(cd packages/scanner-core && python3 -m unittest discover -s tests)
(cd packages/content-engine && python3 -m unittest discover -s tests)
scripts/run-examples.sh
python3 packages/content-engine/archive_fetch.py --help
python3 packages/content-engine/archive_tag.py --help
```

Lint runs in `.venv-lint` on Python 3.10+ (mypy 2.4.0 needs it): check `python --version` there.
No Python 3.10+? Install one first, e.g. `uv python install 3.11` or `brew install python@3.11`.
```sh
python3.11 -m venv .venv-lint && . .venv-lint/bin/activate  # or any python3.10+, e.g. python3.14
pip install ruff==0.16.10 mypy==2.4.0
ruff check .
ruff format --check .
mypy
pip install pip-audit==2.10.1
pip-audit -r packages/scanner-core/requirements.txt
pip install shellcheck-py==0.11.0.1
shellcheck scripts/run-examples.sh examples/*/run.sh
```

## Contract to keep

- Imported pipelines keep config/state in the caller and preflight every host link (`test_pipeline.py`).
- Blog and LinkedIn use full bundled editorial workflows unless a custom writer is explicit.
- No draft without signals and approval: `TestWritingBoundary`, `test_no_signals_section_*`.
- Outside text stays in DATA blocks and cannot approve anything: `TestTrustBoundary`.
- Every documented `write` setting reaches the prompt: `TestFormatSettingsReachThePrompt`.
- An undated post is dropped, never assumed fresh: `TestRedditDates`, the blog-scan tests.
- One failing source never stops the others, and each failed request is in `failures`:
  `TestAllPlatformsKeepWhatWorked`, `TestFailuresAreInTheOutput`, `TestScan`, `TestSitemap`.
- Scripts fail with a non-zero exit and a message: for example `TestScoreRangeAndExitCode`.
- A first-person post never gets an invented story, and an Author's take is argued as
  opinion: `TestAuthorsTake`, and the LinkedIn POV cases in `TestFormatSettingsReachThePrompt`.
- Requested changes beat format settings, not rules: `TestRequestedChangesOverrideSettings`.
- Voice examples match the theme's type, then category, then closest type, read whole, and
  none when nothing matches: `TestMatchedExamples`. A post is tagged once: `test_archive_tag.py`.
- Tests never reach the network or a real key: each `tests/_guard.py`, checked by `TestGuard`.
- Public contract (semver 0.x): command, modes, flags, `.env` and config keys, output JSON.

## Making a change

- Write the test first. A behaviour change needs a case that fails before and passes after.
  Scanner cases go in `test_scan_paths.py`, script cases in the matching `test_<script>.py`.
- Stub every HTTP call (`sc.http_json`, `sc.gql`, `_fetch`, `af.fetch`, `urlopen`).
- A user-visible change adds an `[Unreleased]` line to `CHANGELOG.md`. Tests, docs, examples don't.
- After editing the command file, dry-run it in a fresh clone: only `working/` may change.
- Examples never reach a live host: read a local file, serve on 127.0.0.1, or stub `urlopen`.
- A new example: a folder (lowercase, digits, hyphens), an executable `run.sh` with no license
  header, a README like `examples/count-signals-and-themes/README.md` (paragraph, `sh` block, a
  `text` block of stdout), an index row `| <want> | [<folder>](<folder>/) |`, output in `working/`.

## Do not

- During contributor tests and audits, use `--dry-run` unless a live run is explicitly authorized.
  An explicitly authorized live or scheduled run may execute the requested mode.
  This does not independently authorize Slack delivery, publishing or scheduling.
- Never print the values in `packages/content-engine/.env`.
- Do not call Product Hunt or X for real. Both cost money or need a personal token.
- Do not edit the `.example` files to suit one test. Tests and examples read them as shipped.
