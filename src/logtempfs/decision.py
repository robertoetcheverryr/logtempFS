import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import psutil
from dmemfs import MemoryFileSystem, expand_archive_streaming

from logtempfs.mem import MemTempFS
from logtempfs.real import RealTempFS


def _available_memory_gb() -> float:
    """Cross-platform available memory in GB."""
    return psutil.virtual_memory().available / (1024**3)


def _extract_to_dir(archive_path: Path, target_dir: Path) -> None:
    """Extract a tar/tgz archive into a real directory."""
    kwargs: dict[str, Any] = {}
    if sys.version_info >= (3, 12):
        kwargs["filter"] = "data"
    with tarfile.open(archive_path, "r:*") as tar:
        tar.extractall(target_dir, **kwargs)


def _run(cmd: list[str]) -> bool:
    """Run a command, return True on success."""
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


@contextmanager
def create_temp_fs(
    archive_path: Path,
    *,
    prefer_memory: bool = True,
    min_free_gb: float = 4.0,
) -> Iterator[MemTempFS | RealTempFS]:
    """
    Yield a TempFS that already contains the extracted archive.

    Preference order:
    1. MemTempFS (D-MemFS) when enough RAM is available
    2. RealTempFS on /dev/shm (Linux, non-root) when enough RAM is available
    3. RealTempFS on a normal temporary directory
    """
    archive_size_gb = archive_path.stat().st_size / (1024**3)
    needed_gb = max(2.0, archive_size_gb * 3)
    available = _available_memory_gb()

    mfs = None
    mount_point = None
    tmp_dir = None
    fs: MemTempFS | RealTempFS | None = None

    try:
        # 1. Try MemTempFS
        if prefer_memory and available > (needed_gb + min_free_gb):
            try:
                mfs = MemoryFileSystem(max_quota=int(needed_gb * 1024**3))
                expand_archive_streaming(mfs, str(archive_path), dest="/data")
                print(f"Using MemTempFS (quota {needed_gb:.1f} GB)")
                fs = MemTempFS(mfs, root="/data")
            except Exception as e:
                print(f"WARNING: MemTempFS failed ({e}). Falling back.")
                mfs = None

        # 2. Try Linux /dev/shm (tmpfs, no root required)
        if fs is None and platform.system() == "Linux" and available > (needed_gb + min_free_gb):
            shm = Path("/dev/shm")
            if shm.is_dir() and os.access(shm, os.W_OK):
                try:
                    mount_point = Path(tempfile.mkdtemp(prefix="logtempfs_ram_", dir=shm))
                    _extract_to_dir(archive_path, mount_point)
                    print(f"Using /dev/shm ({needed_gb:.1f} GB requested)")
                    fs = RealTempFS(mount_point)
                except Exception as e:
                    print(f"WARNING: /dev/shm failed ({e}). Falling back.")
                    if mount_point is not None:
                        shutil.rmtree(mount_point, ignore_errors=True)
                        mount_point = None

        # 3. Normal temporary directory
        if fs is None:
            print("Using normal temporary directory")
            tmp_dir = tempfile.TemporaryDirectory(prefix="logtempfs_")
            extract_dir = Path(tmp_dir.name)
            _extract_to_dir(archive_path, extract_dir)
            fs = RealTempFS(extract_dir)

        if fs is None:
            raise RuntimeError(
                "Failed to create any temporary filesystem (this should be unreachable)"
            )

        yield fs

    finally:
        if mount_point is not None:
            shutil.rmtree(mount_point, ignore_errors=True)
        if tmp_dir is not None:
            tmp_dir.cleanup()
