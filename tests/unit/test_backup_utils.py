"""验证数据快照的完整性校验和恢复流程。"""

from __future__ import annotations

import sqlite3
import zipfile
from pathlib import Path

from app.core.config import Settings
from scripts.backup_utils import create_backup, restore_backup, verify_backup


def _settings(root: Path) -> Settings:
    """构造所有持久化数据都位于临时项目目录的配置。"""
    return Settings(
        _env_file=None,
        app_version="0.5.0",
        database_url="sqlite:///./data/app.db",
        documents_path=Path("data/documents"),
        chroma_path=Path("data/chroma"),
        tts_cache_path=Path("data/tts-cache"),
        resume_file_path=Path("output/resume.pdf"),
        candidate_profile_path=Path("data/candidate_profile.json"),
    )


def test_backup_and_restore_all_persistent_components(tmp_path: Path) -> None:
    """快照恢复后数据库和各类文件都应回到备份时内容。"""
    settings = _settings(tmp_path)
    data = tmp_path / "data"
    (data / "documents").mkdir(parents=True)
    (data / "chroma").mkdir()
    (data / "tts-cache").mkdir()
    (tmp_path / "output").mkdir()
    (data / "documents/note.txt").write_text("原始文档", encoding="utf-8")
    (data / "chroma/index.bin").write_bytes(b"vector")
    (data / "tts-cache/speech.mp3").write_bytes(b"audio")
    (data / "candidate_profile.json").write_text('{"name":"曾有为"}', encoding="utf-8")
    (tmp_path / "output/resume.pdf").write_bytes(b"%PDF-test")
    with sqlite3.connect(data / "app.db") as connection:
        connection.execute("CREATE TABLE sample (value TEXT)")
        connection.execute("INSERT INTO sample VALUES ('before')")

    archive = create_backup(settings, tmp_path, tmp_path / "backups", label="test")
    manifest = verify_backup(archive)
    assert manifest["app_version"] == "0.5.0"
    assert len(manifest["files"]) == 6

    (data / "documents/note.txt").write_text("已修改", encoding="utf-8")
    with sqlite3.connect(data / "app.db") as connection:
        connection.execute("UPDATE sample SET value='after'")
    restore_backup(archive, settings, tmp_path, apply=True)

    assert (data / "documents/note.txt").read_text(encoding="utf-8") == "原始文档"
    with sqlite3.connect(data / "app.db") as connection:
        assert connection.execute("SELECT value FROM sample").fetchone()[0] == "before"


def test_restore_defaults_to_validation_only(tmp_path: Path) -> None:
    """未显式 apply 时只校验归档，不修改当前数据。"""
    settings = _settings(tmp_path)
    (tmp_path / "data/documents").mkdir(parents=True)
    (tmp_path / "data/documents/note.txt").write_text("备份内容", encoding="utf-8")
    archive = create_backup(settings, tmp_path, tmp_path / "backups", label="dry-run")
    (tmp_path / "data/documents/note.txt").write_text("当前内容", encoding="utf-8")

    restore_backup(archive, settings, tmp_path)

    assert (tmp_path / "data/documents/note.txt").read_text(encoding="utf-8") == "当前内容"


def test_verify_backup_rejects_changed_content(tmp_path: Path) -> None:
    """归档内容被修改后必须因哈希不一致而拒绝恢复。"""
    settings = _settings(tmp_path)
    (tmp_path / "data/documents").mkdir(parents=True)
    (tmp_path / "data/documents/note.txt").write_text("可信内容", encoding="utf-8")
    archive = create_backup(settings, tmp_path, tmp_path / "backups", label="tampered")
    changed_archive = tmp_path / "changed.zip"

    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(changed_archive, "w") as target:
        for name in source.namelist():
            content = source.read(name)
            if name.endswith("note.txt"):
                content = b"x" * len(content)
            target.writestr(name, content)

    try:
        verify_backup(changed_archive)
    except ValueError as exc:
        assert "哈希不一致" in str(exc)
    else:
        raise AssertionError("被篡改的备份不应通过校验")


def test_verify_backup_rejects_path_traversal(tmp_path: Path) -> None:
    """包含目录穿越路径的伪造归档必须在解压前被拒绝。"""
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("manifest.json", '{"schema_version": 1, "files": []}')
        bundle.writestr("../outside.txt", "unsafe")

    try:
        verify_backup(archive)
    except ValueError as exc:
        assert "结构不安全" in str(exc)
    else:
        raise AssertionError("危险归档路径不应通过校验")
