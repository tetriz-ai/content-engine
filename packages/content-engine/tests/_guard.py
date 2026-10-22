# Copyright 2026 Workloom Solutions Private Limited
# SPDX-License-Identifier: MIT
"""Test-wide guard, imported first by every test module.

HOME points at a fresh temp dir, the credential variables are unset, the
scripts' `.env` lookup points at a file that does not exist, and every
socket connection raises, so a test that forgets its fake can reach neither
a real key nor the network.
"""

import atexit
import os
import shutil
import socket
import subprocess
import sys
import tempfile

HOME = tempfile.mkdtemp(prefix="content-engine-test-home-")
atexit.register(shutil.rmtree, HOME, True)
os.environ["HOME"] = HOME
os.environ["USERPROFILE"] = HOME
for _var in (
    "ANTHROPIC_API_KEY",
    "PH_API_TOKEN",
    "TWITTER_BEARER_TOKEN",
    "CONTENT_ENGINE_SLACK_CHANNEL",
):
    os.environ.pop(_var, None)


def _blocked(*args, **kwargs):
    raise RuntimeError("network access is blocked in tests")


socket.socket.connect = _blocked
socket.socket.connect_ex = _blocked
socket.create_connection = _blocked
socket.getaddrinfo = _blocked

# Child fetch processes would not inherit the socket monkeypatch above.
_original_run = subprocess.run


def _guarded_run(args, *a, **kwargs):
    if isinstance(args, (list, tuple)) and "--reddit-fetch-worker" in args:
        raise RuntimeError("network access is blocked in tests")
    return _original_run(args, *a, **kwargs)


subprocess.run = _guarded_run

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import archive_tag  # noqa: E402
import relevance_scorer  # noqa: E402
import write_reference  # noqa: E402

NO_ENV_FILE = os.path.join(HOME, "no-such.env")
write_reference.ENV_FILE = NO_ENV_FILE
relevance_scorer.ENV_FILE = NO_ENV_FILE
archive_tag.ENV_FILE = NO_ENV_FILE
