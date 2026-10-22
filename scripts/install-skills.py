#!/usr/bin/env python3
# Copyright 2026 Workloom Solutions Private Limited
# SPDX-License-Identifier: MIT
"""Link the bundled pipeline into a caller repository without creating runtime state."""

import argparse
import json
import os
import sys
from pathlib import Path


def install(target, root):
    manifest = json.loads((root / "pipeline-manifest.json").read_text(encoding="utf-8"))
    links = []
    for host in (".agents", ".claude"):
        parent = target / host / "skills"
        for component in (target / host, parent):
            if component.is_symlink():
                raise ValueError("Skill destination cannot use a symlink parent: %s" % component)
        for name, relative in manifest["skills"].items():
            source = (root / relative).resolve()
            if not (source / "SKILL.md").is_file():
                raise ValueError("Missing skill entrypoint: %s" % source)
            link = parent / name
            if os.path.lexists(link):
                if not link.is_symlink() or link.resolve() != source:
                    raise ValueError("Existing skill would be replaced; preserve it: %s" % link)
            else:
                links.append((link, source))
    created = []
    try:
        for link, source in links:
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(os.path.relpath(source, link.parent), target_is_directory=True)
            created.append(link)
    except OSError:
        for link in reversed(created):
            link.unlink()
        raise
    return {"status": "linked", "hosts": ["claude", "codex"], "skills": manifest["skills"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--into", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(
            json.dumps(install(args.into.resolve(strict=True), Path(__file__).resolve().parents[1]))
        )
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
