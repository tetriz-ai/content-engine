#!/bin/sh
# Saves the posts in a sample feed as a writer archive, then prints the saved files.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/profile.yaml" <<YAML
archive_dir: $tmp/archive
archive_sources:
  - rss: file://$here/feed.xml
YAML
python3 packages/content-engine/archive_fetch.py --profile "$tmp/profile.yaml" \
  | sed -e "s#$tmp#<tmp>#g" -e "s#file://$here#file://examples/save-your-own-posts#g"
ls "$tmp/archive"
echo
cat "$tmp/archive/2026-09-29-why-i-stopped-re-running-red-builds.md"
