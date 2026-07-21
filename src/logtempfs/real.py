from pathlib import Path


class RealTempFS:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def _resolve(self, rel_path: str) -> Path:
        path = (self.root / rel_path).resolve()
        if not str(path).startswith(str(self.root)):
            raise ValueError(f"Path escapes root: {rel_path}")
        return path

    def read_text(self, rel_path: str, encoding: str = "utf-8") -> str:
        return self._resolve(rel_path).read_text(encoding=encoding, errors="replace")

    def read_bytes(self, rel_path: str) -> bytes:
        return self._resolve(rel_path).read_bytes()

    def exists(self, rel_path: str) -> bool:
        return self._resolve(rel_path).exists()

    def listdir(self, rel_path: str = "") -> list[str]:
        p = self._resolve(rel_path)
        return sorted(x.name for x in p.iterdir())

    def rglob(self, pattern: str) -> list[str]:
        results = []
        for path in self.root.rglob(pattern):
            if path.is_file():
                results.append(str(path.relative_to(self.root)).replace("\\", "/"))
        return sorted(results)
