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

    # 1. Pure in-memory (D-MemFS)
    if prefer_memory and available > (needed_gb + min_free_gb):
        try:
            mfs = MemoryFileSystem(max_quota=int(needed_gb * 1024**3))
            expand_archive_streaming(mfs, archive_path, dest="/data")
            print(f"Using MemTempFS (quota {needed_gb:.1f} GB)")
            yield MemTempFS(mfs, root="/data")
            return
        except Exception as e:
            print(f"WARNING: MemTempFS failed ({e}). Falling back.")

    # 2. Linux tmpfs
    if platform.system() == "Linux" and available > (needed_gb + min_free_gb):
        mount_point = Path(tempfile.mkdtemp(prefix="logtempfs_ram_"))
        size_arg = f"{needed_gb:.1f}G"
        rc = os.system(f"mount -t tmpfs -o size={size_arg} tmpfs '{mount_point}'")
        if rc == 0:
            try:
                _extract_to_dir(archive_path, mount_point)
                print(f"Using Linux tmpfs ({size_arg})")
                yield RealTempFS(mount_point)
            finally:
                os.system(f"umount '{mount_point}' 2>/dev/null")
                shutil.rmtree(mount_point, ignore_errors=True)
            return
        else:
            shutil.rmtree(mount_point, ignore_errors=True)
            print("WARNING: tmpfs mount failed. Falling back to normal temp dir.")

    # 3. Normal temporary directory
    print("Using normal temporary directory")
    with tempfile.TemporaryDirectory(prefix="logtempfs_") as tmp:
        extract_dir = Path(tmp)
        _extract_to_dir(archive_path, extract_dir)
        yield RealTempFS(extract_dir)
