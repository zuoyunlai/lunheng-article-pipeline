"""Shared hermetic test helpers.

The repository may contain maintainer-only untracked files while tests run.
Sandbox copies must be derived from Git's tracked-file set, not copytree(ROOT),
so external workspace dirt cannot change a test's result.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess


def tracked_tree(root: pathlib.Path, dest: pathlib.Path) -> pathlib.Path:
    """Copy the current contents of Git-tracked files into *dest*.

    Unlike ``shutil.copytree`` this excludes untracked workspace artifacts while
    preserving edits to tracked files (important for mutation tests).
    """
    root = pathlib.Path(root).resolve()
    dest = pathlib.Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    raw = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    for encoded in raw.split(b"\0"):
        if not encoded:
            continue
        rel = os.fsdecode(encoded)
        src = root / rel
        dst = dest / rel
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return dest
