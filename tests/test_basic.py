import tarfile
from pathlib import Path

from logtempfs import create_temp_fs
from logtempfs.mem import MemTempFS
from logtempfs.real import RealTempFS


def _make_test_tgz(tmp_path: Path) -> Path:
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "hello.txt").write_text("hello from archive", encoding="utf-8")
    (content_dir / "subdir").mkdir()
    (content_dir / "subdir" / "nested.txt").write_text(
        "nested content", encoding="utf-8"
    )

    tgz_path = tmp_path / "test_archive.tgz"
    with tarfile.open(tgz_path, "w:gz") as tar:
        tar.add(content_dir / "hello.txt", arcname="hello.txt")
        tar.add(content_dir / "subdir" / "nested.txt", arcname="subdir/nested.txt")
    return tgz_path


def _assert_contents(fs):
    assert fs.exists("hello.txt")
    assert fs.read_text("hello.txt") == "hello from archive"
    assert fs.exists("subdir/nested.txt")
    assert fs.read_text("subdir/nested.txt") == "nested content"
    assert "hello.txt" in fs.listdir("")
    assert "subdir" in fs.listdir("")
    found = fs.rglob("*.txt")
    assert "hello.txt" in found
    assert "subdir/nested.txt" in found


class TestCreateTempFS:
    def test_mem_temp_fs_path(self, tmp_path: Path):
        """Force the D-MemFS (in-memory) backend."""
        tgz = _make_test_tgz(tmp_path)

        with create_temp_fs(tgz, prefer_memory=True, min_free_gb=0.0) as fs:
            assert isinstance(fs, MemTempFS)
            _assert_contents(fs)

    def test_real_temp_fs_path(self, tmp_path: Path):
        """Force the real filesystem backend."""
        tgz = _make_test_tgz(tmp_path)

        with create_temp_fs(tgz, prefer_memory=False) as fs:
            assert isinstance(fs, RealTempFS)
            _assert_contents(fs)

    def test_real_temp_fs_basic(self, tmp_path: Path):
        (tmp_path / "hello.txt").write_text("world", encoding="utf-8")
        fs = RealTempFS(tmp_path)
        assert fs.read_text("hello.txt") == "world"
        assert fs.exists("hello.txt")
        assert "hello.txt" in fs.listdir()
        assert fs.rglob("*.txt") == ["hello.txt"]
