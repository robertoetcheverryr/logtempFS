# logtempFS

[![CI](https://github.com/robertoetcheverryr/logtempFS/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/robertoetcheverryr/logtempFS/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/robertoetcheverryr/logtempFS/branch/master/graph/badge.svg)](https://codecov.io/gh/robertoetcheverryr/logtempFS)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Temporary filesystem abstraction for large log archives.

Give it an archive and get back a ready-to-use filesystem that contains the extracted contents.

## Backends

1. **MemTempFS** – pure in-memory via D-MemFS (when enough RAM is available)
2. **RealTempFS** – normal temporary directory (fallback)

The caller never has to care which backend was chosen.

## AI usage disclosure

AI assisted - Human reviewed

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
