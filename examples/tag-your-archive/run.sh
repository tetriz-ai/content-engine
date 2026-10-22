#!/bin/sh
# Tags a small sample archive from a saved answer, then shows which posts the writer picks
# as voice examples for a theme of the same type and category.
set -eu
here=examples/tag-your-archive
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cp -R "$here/archive" "$tmp/archive"
cat > "$tmp/profile.yaml" <<YAML
archive_dir: $tmp/archive
content_types: [postmortem, checklist, personal story, other]
max_examples: 3
YAML
python3 packages/content-engine/archive_tag.py --profile "$tmp/profile.yaml" \
  --response-file "$here/answer.txt" | sed "s#$tmp#<tmp>#g"
python3 packages/content-engine/archive_tag.py --profile "$tmp/profile.yaml" --list
# The writer prints its prompt on standard output and the voice-examples line on standard error.
{ python3 packages/content-engine/write_reference.py --theme-doc "$here/theme.md" --format blog \
  --profile "$tmp/profile.yaml" --dry-run >/dev/null; } 2>&1
