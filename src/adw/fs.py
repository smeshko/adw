"""Atomic file writes for run and user state."""

import os
import secrets
import stat
from pathlib import Path


def atomic_write(path: Path, data: str | bytes) -> None:
    """Replace ``path`` with ``data`` so readers see the old or new file, never half.

    Writes a temp file next to ``path``, fsyncs it and renames it over the
    target. A replaced file keeps its mode; a new one gets the umask default
    (``mkstemp`` would make it 0600). ``str`` data is written as UTF-8. The
    parent directory must exist.

    Raises:
        OSError: If the write or the rename fails. The old file is untouched
            and the temp file is removed.
    """
    tmp = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
    try:
        with os.fdopen(fd, "wb") as f:
            if path.exists():
                os.fchmod(f.fileno(), stat.S_IMODE(path.stat().st_mode))
            f.write(data.encode("utf-8") if isinstance(data, str) else data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
