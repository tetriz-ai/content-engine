Scores a candidate theme against the sample writer profile without an Anthropic API key. The scorer reads a saved answer instead of calling the API, which is the path a Claude Code session takes when no key is set. The answer here is fixed, so this shows the output format, not the model's judgement.

```sh
examples/score-a-theme-without-an-api-key/run.sh
```

```text
{
  "score": 8,
  "fit": true,
  "why": "Flaky tests and CI re-runs are the core of the writer's CI reliability beat."
}
```
