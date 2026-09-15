"""创建 ZYW 的 AI 小助理完整数据备份。"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import get_settings
from scripts.backup_utils import create_backup, verify_backup


def main() -> int:
    """解析参数、创建快照并立即执行完整性校验。"""
    parser = argparse.ArgumentParser(description="备份 SQLite、文档、Chroma 和公开资源")
    parser.add_argument("--output-dir", type=Path, default=Path("backups"))
    parser.add_argument("--label", default="manual")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    archive = create_backup(
        get_settings(), root, arguments.output_dir, label=arguments.label
    )
    manifest = verify_backup(archive)
    print(f"备份已生成：{archive}")
    print(f"已校验文件数：{len(manifest['files'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

