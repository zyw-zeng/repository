"""创建和恢复带哈希清单的应用数据快照。"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy.engine import make_url

from app.core.config import Settings

MANIFEST_NAME = "manifest.json"
SNAPSHOT_PREFIX = "snapshot"


@dataclass(frozen=True)
class BackupTargets:
    """记录当前环境中各持久化组件的实际路径。"""

    database: Path
    documents: Path
    chroma: Path
    tts_cache: Path
    resume: Path
    candidate_profile: Path


def _resolve_path(path: Path, project_root: Path) -> Path:
    """把相对配置路径稳定解析到项目根目录。"""
    return path.resolve() if path.is_absolute() else (project_root / path).resolve()


def resolve_targets(settings: Settings, project_root: Path) -> BackupTargets:
    """从配置中解析数据库、知识库、语音缓存和公开资源路径。"""
    root = project_root.resolve()
    database_url = make_url(settings.database_url)
    if not database_url.drivername.startswith("sqlite") or not database_url.database:
        raise ValueError("v0.5 备份工具仅支持 SQLite 数据库")
    database = Path(database_url.database)
    return BackupTargets(
        database=_resolve_path(database, root),
        documents=_resolve_path(settings.documents_path, root),
        chroma=_resolve_path(settings.chroma_path, root),
        tts_cache=_resolve_path(settings.tts_cache_path, root),
        resume=_resolve_path(settings.resume_file_path, root),
        candidate_profile=_resolve_path(settings.candidate_profile_path, root),
    )


def sha256_file(path: Path) -> str:
    """分块计算文件哈希，避免大文件一次性进入内存。"""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_sqlite(source: Path, destination: Path) -> None:
    """使用 SQLite 在线备份 API 生成事务一致的数据库副本。"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        return
    source_connection = sqlite3.connect(source)
    destination_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()


def _copy_component(source: Path, destination: Path) -> None:
    """复制文件或目录，不跟随不存在的可选组件。"""
    if not source.exists():
        return
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _component_sources(targets: BackupTargets) -> dict[str, Path]:
    return {
        "database": targets.database,
        "documents": targets.documents,
        "chroma": targets.chroma,
        "tts_cache": targets.tts_cache,
        "resume": targets.resume,
        "candidate_profile": targets.candidate_profile,
    }


def _snapshot_component_path(snapshot_root: Path, component: str, source: Path) -> Path:
    """为每个组件分配稳定且不泄露服务器绝对路径的归档位置。"""
    if component in {"database", "resume", "candidate_profile"}:
        return snapshot_root / component / source.name
    return snapshot_root / component


def _build_manifest(snapshot_root: Path, app_version: str) -> dict[str, Any]:
    """为快照中的每个文件记录大小和 SHA-256。"""
    files = []
    for path in sorted(item for item in snapshot_root.rglob("*") if item.is_file()):
        relative = path.relative_to(snapshot_root.parent).as_posix()
        component = path.relative_to(snapshot_root).parts[0]
        component_relative = Path(*path.relative_to(snapshot_root).parts[1:]).as_posix()
        files.append(
            {
                "archive_path": relative,
                "component": component,
                "relative_path": component_relative,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {
        "schema_version": 1,
        "app_version": app_version,
        "created_at": datetime.now(UTC).isoformat(),
        "files": files,
    }


def create_backup(
    settings: Settings,
    project_root: Path,
    output_dir: Path,
    *,
    label: str = "manual",
) -> Path:
    """创建包含数据库、文档、索引和公开资源的 ZIP 快照。"""
    root = project_root.resolve()
    destination_dir = output_dir.resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive = destination_dir / f"zyw-ai-assistant-{label}-{timestamp}.zip"
    targets = resolve_targets(settings, root)

    with tempfile.TemporaryDirectory(prefix="zyw-backup-") as temporary:
        staging = Path(temporary)
        snapshot_root = staging / SNAPSHOT_PREFIX
        snapshot_root.mkdir()
        for component, source in _component_sources(targets).items():
            target = _snapshot_component_path(snapshot_root, component, source)
            if component == "database":
                _copy_sqlite(source, target)
            else:
                _copy_component(source, target)
        manifest = _build_manifest(snapshot_root, settings.app_version)
        (staging / MANIFEST_NAME).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary_archive = archive.with_suffix(".tmp")
        with zipfile.ZipFile(temporary_archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(staging / MANIFEST_NAME, MANIFEST_NAME)
            for path in sorted(item for item in snapshot_root.rglob("*") if item.is_file()):
                bundle.write(path, path.relative_to(staging).as_posix())
        os.replace(temporary_archive, archive)
    return archive


def _safe_archive_name(name: str) -> bool:
    """拒绝绝对路径和目录穿越，避免恶意备份包覆盖任意文件。"""
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and "\\" not in name


def verify_backup(archive: Path) -> dict[str, Any]:
    """验证归档结构、文件大小和哈希，返回可信清单。"""
    if not archive.is_file():
        raise FileNotFoundError(f"备份文件不存在：{archive}")
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        if MANIFEST_NAME not in names or any(not _safe_archive_name(name) for name in names):
            raise ValueError("备份包结构不安全或缺少 manifest.json")
        manifest = json.loads(bundle.read(MANIFEST_NAME).decode("utf-8"))
        if manifest.get("schema_version") != 1:
            raise ValueError("不支持的备份清单版本")
        for entry in manifest.get("files", []):
            archive_path = entry["archive_path"]
            if archive_path not in names or not _safe_archive_name(archive_path):
                raise ValueError(f"备份清单文件缺失：{archive_path}")
            content = bundle.read(archive_path)
            if len(content) != entry["size"]:
                raise ValueError(f"备份文件大小不一致：{archive_path}")
            if hashlib.sha256(content).hexdigest() != entry["sha256"]:
                raise ValueError(f"备份文件哈希不一致：{archive_path}")
    return manifest


def _assert_restore_target(path: Path, project_root: Path) -> None:
    """阻止把恢复目标错误指向磁盘根目录、用户目录或项目根目录。"""
    resolved = path.resolve()
    forbidden = {Path(resolved.anchor).resolve(), Path.home().resolve(), project_root.resolve()}
    if resolved in forbidden or len(resolved.parts) < 3:
        raise ValueError(f"拒绝使用危险恢复目标：{resolved}")


def _replace_file(source: Path, target: Path) -> None:
    """先写入同目录临时文件，再原子替换正式文件。"""
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.restore-tmp")
    shutil.copy2(source, temporary)
    os.replace(temporary, target)


def _restore_sqlite(source: Path, target: Path) -> None:
    """通过 SQLite 备份 API 回写数据库，避免 Windows 文件句柄导致替换失败。"""
    target.parent.mkdir(parents=True, exist_ok=True)
    source_connection = sqlite3.connect(source)
    target_connection = sqlite3.connect(target)
    try:
        source_connection.backup(target_connection)
    finally:
        target_connection.close()
        source_connection.close()


def _replace_directory(source: Path, target: Path) -> None:
    """在已有安全备份后，用快照目录完整替换目标目录。"""
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_name(f".{target.name}.restore-tmp")
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(source, staging)
    if target.exists():
        shutil.rmtree(target)
    os.replace(staging, target)


def restore_backup(
    archive: Path,
    settings: Settings,
    project_root: Path,
    *,
    apply: bool = False,
) -> dict[str, Any]:
    """校验备份；只有 apply=True 时才替换当前持久化数据。"""
    manifest = verify_backup(archive)
    if not apply:
        return manifest
    root = project_root.resolve()
    targets = resolve_targets(settings, root)
    component_targets = _component_sources(targets)
    for target in component_targets.values():
        _assert_restore_target(target, root)

    with tempfile.TemporaryDirectory(prefix="zyw-restore-") as temporary:
        staging = Path(temporary)
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(staging)
        snapshot_root = staging / SNAPSHOT_PREFIX
        for component, target in component_targets.items():
            source_root = snapshot_root / component
            if not source_root.exists():
                continue
            if component in {"database", "resume", "candidate_profile"}:
                files = [item for item in source_root.iterdir() if item.is_file()]
                if len(files) != 1:
                    raise ValueError(f"组件文件数量异常：{component}")
                if component == "database":
                    _restore_sqlite(files[0], target)
                else:
                    _replace_file(files[0], target)
            else:
                _replace_directory(source_root, target)
    return manifest
