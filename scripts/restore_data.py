"""校验或恢复 ZYW 的 AI 小助理数据备份。"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import get_settings
from scripts.backup_utils import create_backup, restore_backup


def main() -> int:
    """默认只校验；显式传入 --apply 后先安全备份再恢复。"""
    parser = argparse.ArgumentParser(description="校验或恢复应用数据备份")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--apply", action="store_true", help="停止服务后执行真实恢复")
    parser.add_argument("--safety-backup-dir", type=Path, default=Path("backups"))
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    settings = get_settings()
    if arguments.apply:
        safety = create_backup(
            settings, root, arguments.safety_backup_dir, label="pre-restore"
        )
        print(f"恢复前安全备份：{safety}")
    manifest = restore_backup(arguments.archive, settings, root, apply=arguments.apply)
    action = "恢复完成" if arguments.apply else "校验通过，未修改当前数据"
    print(f"{action}：{arguments.archive}")
    print(f"清单文件数：{len(manifest['files'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

