#!/bin/sh
python3 packages/content-engine/report.py \
  --bank packages/content-engine/examples/content-signal-bank.example.jsonl \
  --themes-dir packages/content-engine/examples
