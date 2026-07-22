# logtempfs

Temporary filesystem abstraction for large log archives.

Give it an archive → get back a ready-to-use filesystem that already contains the extracted contents.

## Backends

1. **MemTempFS** – pure in-memory via D-MemFS (when enough RAM is available)
2. **RealTempFS on `/dev/shm`** – Linux tmpfs, no root required (when enough RAM is available)
3. **RealTempFS** – normal temporary directory (fallback)

The caller never has to care which backend was chosen.

## Quick usage

```python
from pathlib import Path
from logtempfs import create_temp_fs

archive = Path("snap.tgz")

with create_temp_fs(archive) as fs:
    print(fs.listdir(""))
    print(fs.read_text("some/file.txt"))
    for path in fs.rglob("*Nn_stats*"):
        print(path)
