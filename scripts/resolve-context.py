#!/usr/bin/env python3
# Copyright 2026 Workloom Solutions Private Limited
# SPDX-License-Identifier: MIT
"""Resolve engine resources separately from the caller's config and output paths."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--working-root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    working = args.working_root.resolve(strict=True)
    config = args.config or Path("packages/content-engine/config.yaml")
    if not config.is_absolute():
        config = working / config
    print(
        json.dumps(
            {
                "engine_root": str(root),
                "working_root": str(working),
                "config_path": str(config.resolve()),
                "config_exists": config.is_file(),
                "working_dir": str(working / "working"),
                "rules": str(root / "packages/content-engine/rules.md"),
                "blog": str(root / "skills/blog/SKILL.md"),
                "editorial-draft": str(root / "skills/editorial-draft/SKILL.md"),
                # Deprecated resource key for existing importing applications.
                "articleforge": str(root / "skills/editorial-draft/SKILL.md"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
