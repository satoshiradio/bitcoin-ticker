import json
import os


def atomic_write(path, obj):
    """
    Write `obj` as JSON to `path` without ever leaving a half-written file
    behind: dump to a temporary file first, then rename it over the target.
    A power loss mid-write costs the update, not the existing file.
    """
    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(obj, f)
    try:
        os.rename(tmp_path, path)
    except OSError:
        # Some filesystems refuse to rename onto an existing file.
        try:
            os.remove(path)
        except OSError:
            pass
        os.rename(tmp_path, path)
