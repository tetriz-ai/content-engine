#!/bin/sh
python3 packages/content-engine/write_reference.py \
  --theme-doc packages/content-engine/examples/theme-example-ci-flakiness.md \
  --format linkedin \
  --config packages/content-engine/config.example.yaml \
  --dry-run
