import os
import platform
import shutil
import tarfile
import tempfile
from contextlib import contextmanager
from pathlib import Path

import psutil
from dmemfs import MemoryFileSystem, expand_archive_streaming

from logtempfs.mem import MemTempFS
from logtempfs.real import RealTempFS


def _available_memory_gb() -> float:
    """Cross-platform available memory in GB."""
    return psutil.virtual_memory().available / (1024**3)


def _extract_to_dir(archive_path: Path, target_dir: Path) -> None:
    """Extract a tar/tgz archive into a real directory."""
    with tarfile.open(archive_path, "r:*") as tar:
        tar.extractall(target_dir)


@contextmanager
def create_temp_fs(
    archive_path: Path,
    *,
    prefer_memory: bool = True,
    min_free_gb: float = 4.0,
):
    """
    Yield a TempFS that already contains the extracted archive.

    Preference order:
    1. MemTempFS (D-MemFS) when enough RAM is available
    2. RealTempFS on a Linux tmpfs when enough RAM is available
    3. RealTempFS on a normal temporary directory
    """
    archive_size_gb = archive_path.stat().st_size / (1024**3)
    needed_gb = max(2.0, archive_size_gb * 3)
    available = _available_memory_gb()

    mfs = None
    mount_point = None
    tmp_dir = None
    fs = None

    try:
        # 1. Try MemTempFS
        if prefer_memory and available > (needed_gb + min_free_gb):
            try:
                mfs = MemoryFileSystem(max_quota=int(needed_gb * 1024**3))
                expand_archive_streaming(mfs, archive_path, dest="/data")
                print(f"Using MemTempFS (quota {needed_gb:.1f} GB)")
                fs = MemTempFS(mfs, root="/data")
            except Exception as e:
                print(f"WARNING: MemTempFS failed ({e}). Falling back.")
                mfs = None

        # 2. Try Linux tmpfs
        if (
            fs is None
            and platform.system() == "Linux"
            and available > (needed_gb + min_free_gb)
        ):
            mount_point = Path(tempfile.mkdtemp(prefix="logtempfs_ram_"))
            size_arg = f"{needed_gb:.1f}G"
            rc = os.system(f"mount -t tmpfs -o size={size_arg} tmpfs '{mount_point}'")
            if rc == 0:
                try:
                    _extract_to_dir(archive_path, mount_point)
                    print(f"Using Linux tmpfs ({size_arg})")
                    fs = RealTempFS(mount_point)
                except Exception:
                    os.system(f"umount '{mount_point}' 2>/dev/null")
                    shutil.rmtree(mount_point, ignore_errors=True)
                    mount_point = None
                    raise
            else:
                shutil.rmtree(mount_point, ignore_errors=True)
                mount_point = None
                print("WARNING: tmpfs mount failed. Falling back to normal temp dir.")

        # 3. Normal temporary directory
        if fs is None:
            print("Using normal temporary directory")
            tmp_dir = tempfile.TemporaryDirectory(prefix="logtempfs_")
            extract_dir = Path(tmp_dir.name)
            _extract_to_dir(archive_path, extract_dir)
            fs = RealTempFS(extract_dir)

        yield fs

    finally:
        if mount_point is not None:
            os.system(f"umount '{mount_point}' 2>/dev/null")
            shutil.rmtree(mount_point, ignore_errors=True)
        if tmp_dir is not None:
            tmp_dir.cleanup()
