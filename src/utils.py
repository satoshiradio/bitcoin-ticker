import json
import os


def atomic_write(path, obj):
    """
    Write `obj` as JSON to `path` without ever leaving a half-written file
    behind: dump to a temporary file first, then rename it over the target.
    A power loss mid-write costs the update, not the existing file.
    """
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(obj, f)
    except Exception:
        # Don't leave a half-written .tmp behind (it would also be in the way
        # of the next write on filesystems without atomic rename).
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise
    try:
        os.rename(tmp_path, path)
    except OSError:
        # FAT - the Pico's filesystem - refuses to rename onto an existing
        # file, so unlink first. Only needed for FAT; not atomic, but there is
        # no alternative there.
        try:
            os.remove(path)
        except OSError:
            pass
        os.rename(tmp_path, path)
