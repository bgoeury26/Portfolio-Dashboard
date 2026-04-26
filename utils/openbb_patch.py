"""
Redirects OpenBB's build lock file from read-only venv to /tmp.
Must be imported before any 'from openbb import obb'.
Patches pathlib.Path.touch + builtins.open at stdlib level.
"""
import builtins, pathlib, tempfile

_TMP = str(pathlib.Path(tempfile.gettempdir()) / "openbb.build.lock")

# --- Patch 1: pathlib.Path.touch ---
_orig_touch = pathlib.Path.touch
def _safe_touch(self, mode=0o666, exist_ok=True):
    if ".build.lock" in str(self):
        self = pathlib.Path(_TMP)
    return _orig_touch(self, mode=mode, exist_ok=exist_ok)
pathlib.Path.touch = _safe_touch

# --- Patch 2: builtins.open ---
_orig_open = builtins.open
def _safe_open(file, mode="r", *args, **kwargs):
    if ".build.lock" in str(file):
        file = _TMP
    return _orig_open(file, mode, *args, **kwargs)
builtins.open = _safe_open
