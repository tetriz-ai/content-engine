# Contributing

Thanks for looking at this. Two packages and one command live here:

- `.claude/commands/content-engine.md` is the `/content-engine` command.
- `packages/content-engine/` holds its config templates, writing rules and helper scripts.
- `packages/scanner-core/` holds the Hacker News, Reddit, Product Hunt and X fetchers.

## Checks before a pull request

Runtime tests and examples need Python 3.9 or newer and PyYAML. From the repo root,
create an isolated environment and install the hash-locked dependency:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install --require-hashes -r packages/scanner-core/requirements-lock.txt
(cd packages/scanner-core && python3 -m unittest discover -s tests)
(cd packages/content-engine && python3 -m unittest discover -s tests)
scripts/run-examples.sh
```

CI runs the tests on Python 3.9, 3.13 and 3.14. After dependency installation,
the tests and examples need no external service or API key; two examples serve
synthetic fixtures on localhost.

Lint uses a separate Python 3.10+ environment because mypy 2.4.0 requires it;
CI runs lint on Python 3.14. For example, with Python 3.11 installed:

```sh
python3.11 -m venv .venv-lint
. .venv-lint/bin/activate
python --version
pip install ruff==0.16.10 mypy==2.4.0
ruff check .
ruff format --check .
mypy
```

Use another installed Python 3.10+ interpreter in place of `python3.11` if needed.
Keep the lint environment active for the additional tools below.

CI also runs `shellcheck scripts/run-examples.sh examples/*/run.sh` with shellcheck 0.11.0.1 (`pip install shellcheck-py==0.11.0.1`). On pull requests, pushes to `main` and weekly, it runs `pip-audit -r packages/scanner-core/requirements.txt` with pip-audit 2.10.1, and a secret scan of the git history with gitleaks 8.30.1. The test and example jobs install PyYAML from `packages/scanner-core/requirements-lock.txt` with `--require-hashes`.

- **Every pull request needs a test.** A behaviour change needs a test that fails before the change and passes after it.
- **Tests never reach the network or a real key.** Each suite's `tests/_guard.py` blocks connections and unsets the keys, and every new test module imports it first. Stub the HTTP call instead.
- **Lint stays on.** A rule that must be off goes in `pyproject.toml` with a comment, never inline.
- **Examples are checked.** If you change what an example prints, update its README's last block.
- **Commits** say what changed in the imperative ("Read Atom feeds"), one change per pull request.
- If you changed the command file, run `/content-engine --dry-run` in Claude Code and check the summary still makes sense.

## Adding a source

Each source in `config.yaml` → `scan` is a self-contained block, and that is the intended extension point. A new source needs:

1. **A fetcher.** Either a small script (see `competitor-blog-scan.py`: fetch, parse, normalise, fail one feed without stopping the others), or a `WebSearch` step in the command file's Phase 1 when no structured feed exists.
2. **A `native_id` scheme,** the dedupe key. Use the source's own stable id when it has one. A normalised URL is the weaker fallback.
3. **Recency enforcement** when the source has no lookback window of its own. Every row needs a real `published_at`, and a row whose date cannot be found is dropped, never assumed fresh.
4. **A block in `config.example.yaml`** with working comments. Fetch the source yourself first and say in a comment what you checked.
5. **Tests** with the HTTP call stubbed, covering a normal result, a failure, and an undated item.

## What this project won't take

- Anything that makes a format publish on its own. Every mode is draft-only.
- A LinkedIn scraper. LinkedIn has no sanctioned read path.

## Open an issue first

- Embeddings or topic-model clustering in place of the model's grouping. It is a bigger change, so discuss it in an issue before a pull request.

## Licensing of contributions

No sign-off line and no separately signed agreement are needed. By opening a pull request you agree that your contribution is released under the project's [LICENSE](LICENSE).

## Reporting a bug or a dead source

Use the bug report template. Report a security vulnerability privately, as [SECURITY.md](SECURITY.md) says, not as an issue.
