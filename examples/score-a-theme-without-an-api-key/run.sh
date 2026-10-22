#!/bin/sh
python3 packages/content-engine/relevance_scorer.py \
  --profile packages/content-engine/writer-profile.example.yaml \
  --title "Flaky tests are a quiet tax on CI" \
  --rationale "Three posts this week on re-running red builds" \
  --response-file examples/score-a-theme-without-an-api-key/answer.txt
