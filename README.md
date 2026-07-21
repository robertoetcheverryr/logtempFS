# logtempfs

Temporary filesystem abstraction for large log archives.

Give it an archive → get back a ready-to-use filesystem that already contains the extracted contents.

## Backends

- **MemTempFS** – pure in-memory via D-MemFS (preferred when enough RAM is available)
- **RealTempFS** – normal temporary directory (or Linux tmpfs)

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
