#!/bin/sh
python3 examples/plug-in-your-own-writer/outline_writer.py \
  --theme-doc packages/content-engine/examples/theme-example-ci-flakiness.md \
  --format blog \
  --out working/examples/outline.md
cat working/examples/outline.md
