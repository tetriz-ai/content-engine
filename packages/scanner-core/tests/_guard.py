# Copyright 2026 Workloom Solutions Private Limited
# SPDX-License-Identifier: MIT
"""Test-wide guard, imported first by every test module.

HOME points at a fresh temp dir, the credential variables are unset, and
every socket connection raises, so a test that forgets its fake can reach
neither a real token nor the network.
"""

import atexit
import os
import shutil
import socket
import subprocess
import tempfile

HOME = tempfile.mkdtemp(prefix="scanner-core-test-home-")
atexit.register(shutil.rmtree, HOME, True)
os.environ["HOME"] = HOME
os.environ["USERPROFILE"] = HOME
for _var in ("PH_API_TOKEN", "TWITTER_BEARER_TOKEN", "ANTHROPIC_API_KEY"):
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
