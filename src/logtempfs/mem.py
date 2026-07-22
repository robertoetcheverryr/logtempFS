import fnmatch

from dmemfs import MemoryFileSystem


class MemTempFS:
    def __init__(self, mfs: MemoryFileSystem, root: str = "/"):
        self.mfs = mfs
        self.root = root.rstrip("/") or ""

    def _full(self, rel_path: str) -> str:
        rel = rel_path.lstrip("/")
        if self.root:
            return f"{self.root}/{rel}" if rel else self.root
        return f"/{rel}" if rel else "/"

    def read_text(self, rel_path: str, encoding: str = "utf-8") -> str:
        with self.mfs.open(self._full(rel_path), "rb") as f:
            return f.read().decode(encoding, errors="replace")

    def read_bytes(self, rel_path: str) -> bytes:
        with self.mfs.open(self._full(rel_path), "rb") as f:
            return f.read()

    def exists(self, rel_path: str) -> bool:
        return self.mfs.exists(self._full(rel_path))

    def listdir(self, rel_path: str = "") -> list[str]:
        return sorted(self.mfs.listdir(self._full(rel_path)))

    def rglob(self, pattern: str) -> list[str]:
        matches = []
        prefix = self.root + "/" if self.root else "/"

        def walk(current: str) -> None:
            for name in self.mfs.listdir(current):
                full = f"{current.rstrip('/')}/{name}"
                rel = (
                    full[len(prefix) :] if full.startswith(prefix) else full.lstrip("/")
                )
                if self.mfs.is_dir(full):
                    walk(full)
                else:
                    if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(name, pattern):
                        matches.append(rel)

        walk(self.root or "/")
        return sorted(matches)
