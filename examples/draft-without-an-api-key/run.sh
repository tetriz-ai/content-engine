#!/bin/sh
python3 packages/content-engine/write_reference.py \
  --theme-doc packages/content-engine/examples/theme-example-ci-flakiness.md \
  --format blog \
  --response-file examples/draft-without-an-api-key/answer.md \
  --out working/examples/draft-without-an-api-key.md
cat working/examples/draft-without-an-api-key.md
