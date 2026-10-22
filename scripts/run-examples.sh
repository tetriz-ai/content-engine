#!/bin/sh
# Copyright 2026 Workloom Solutions Private Limited
# SPDX-License-Identifier: MIT
#
# Runs every example in examples/: takes the sh block from each example's README, runs it
# from the repo root, and compares its standard output with the README's last block. Each
# `generated_at:` value is rewritten to `<time>` first. Fails when the index in
# examples/README.md and the example folders differ.
set -eu
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1

listed=$(sed -n 's/^| .* | \[\([a-z0-9-]*\)\](\([a-z0-9-]*\)\/) |$/\1/p' examples/README.md | sort)
present=$(find examples -mindepth 1 -maxdepth 1 -type d | sed 's#^examples/##' | sort)
if [ "$listed" != "$present" ]; then
  echo "examples/README.md and the example folders differ. Each folder under examples/, named in"
  echo "lowercase letters, digits and hyphens, needs one index row '| <what you want> | [<folder>](<folder>/) |',"
  echo "and each row needs its folder."
  echo "listed:  $(echo "$listed" | tr '\n' ' ')"
  echo "present: $(echo "$present" | tr '\n' ' ')"
  exit 1
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
fail=0
for name in $listed; do
  readme="examples/$name/README.md"
  awk '/^```sh$/ { f = 1; next } /^```$/ { if (f) exit } f' "$readme" > "$tmp/cmd"
  awk '/^```/ { if (f) { f = 0; last = buf } else { f = 1; buf = "" } next }
       f { buf = buf $0 "\n" } END { printf "%s", last }' "$readme" > "$tmp/expected"
  if ! sh "$tmp/cmd" > "$tmp/raw" 2> "$tmp/stderr"; then
    echo "FAIL $name: exited non-zero"
    cat "$tmp/stderr"
    fail=1
    continue
  fi
  sed -E 's/^generated_at: .*/generated_at: <time>/' "$tmp/raw" > "$tmp/actual"
  if diff -u "$tmp/expected" "$tmp/actual" > "$tmp/diff"; then
    echo "ok   $name"
  else
    echo "FAIL $name: output differs from its README"
    cat "$tmp/diff"
    fail=1
  fi
done
exit "$fail"
