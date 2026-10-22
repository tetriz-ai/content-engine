#!/bin/sh
# Saves the posts in a sample Medium export and a sample LinkedIn export, then prints them.
set -eu
here=examples/read-your-exports
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/profile.yaml" <<YAML
archive_dir: $tmp/archive
archive_sources:
  - medium_export: $here/medium-export
  - linkedin_export: $here/linkedin-export
YAML
python3 packages/content-engine/archive_fetch.py --profile "$tmp/profile.yaml" | sed "s#$tmp#<tmp>#g"
ls "$tmp/archive"
echo
cat "$tmp/archive/2025-11-03-how-we-cut-ci-time-in-half.md"
echo
cat "$tmp/archive/2026-03-10-our-build-went-from-22-minutes-to-9.md"
