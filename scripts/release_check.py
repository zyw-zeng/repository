"""执行 v0.5 发布前自动验收，并保存可追溯的 JSON 报告。"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
MAX_CAPTURE_CHARS = 20_000


def _run_check(name: str, command: list[str], cwd: Path) -> dict[str, Any]:
    """执行单项检查；即使失败也继续收集其余项目的结果。"""
    started = time.perf_counter()
    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        output = f"{process.stdout}\n{process.stderr}".strip()
        return {
            "name": name,
            "status": "passed" if process.returncode == 0 else "failed",
            "return_code": process.returncode,
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "command": command,
            "output": output[-MAX_CAPTURE_CHARS:],
        }
    except OSError as exc:
        return {
            "name": name,
            "status": "failed",
            "return_code": None,
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "command": command,
            "output": str(exc),
        }


def _frontend_command(*arguments: str) -> list[str]:
    """定位 pnpm 可执行文件，兼容 Windows 的 pnpm.cmd。"""
    executable = shutil.which("pnpm")
    if not executable:
        raise FileNotFoundError("未找到 pnpm，请先安装 Node.js 与 pnpm")
    return [executable, *arguments]


def build_checks(*, with_evaluation: bool, with_e2e: bool) -> list[tuple[str, list[str], Path]]:
    """构建固定顺序的发布检查，便于本地与服务器得到一致结果。"""
    python = sys.executable
    checks: list[tuple[str, list[str], Path]] = [
        (
            "Python 静态检查",
            [
                python,
                "-m",
                "ruff",
                "check",
                "app",
                "tests",
                "evaluations",
                "scripts",
                "migrations",
                "main.py",
            ],
            PROJECT_ROOT,
        ),
        ("Python 自动化测试", [python, "-m", "pytest"], PROJECT_ROOT),
        ("数据库迁移分支检查", [python, "-m", "alembic", "heads"], PROJECT_ROOT),
        ("前端代码检查", _frontend_command("lint"), FRONTEND_ROOT),
        ("前端类型检查", _frontend_command("typecheck"), FRONTEND_ROOT),
        ("前端组件测试", _frontend_command("test"), FRONTEND_ROOT),
        ("前端生产构建", _frontend_command("build"), FRONTEND_ROOT),
    ]
    if with_e2e:
        checks.append(("前端端到端测试", _frontend_command("test:e2e"), FRONTEND_ROOT))
    if with_evaluation:
        checks.append(("35 题真实模型评测", [python, "evaluations/evaluate.py"], PROJECT_ROOT))
    return checks


def run_release_check(*, with_evaluation: bool, with_e2e: bool, output: Path) -> int:
    """运行全部检查并返回适合命令行使用的退出码。"""
    started = time.perf_counter()
    try:
        checks = build_checks(with_evaluation=with_evaluation, with_e2e=with_e2e)
    except FileNotFoundError as exc:
        print(f"发布检查无法启动：{exc}")
        return 2

    results = []
    for name, command, cwd in checks:
        print(f"[执行] {name}")
        result = _run_check(name, command, cwd)
        results.append(result)
        print(f"[{'通过' if result['status'] == 'passed' else '失败'}] {name}")

    failed = [item["name"] for item in results if item["status"] != "passed"]
    report = {
        "schema_version": 1,
        "release_version": get_settings().app_version,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "passed" if not failed else "failed",
        "duration_ms": round((time.perf_counter() - started) * 1000),
        "with_evaluation": with_evaluation,
        "with_e2e": with_e2e,
        "failed_checks": failed,
        "checks": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"发布报告：{output.resolve()}")
    return 0 if not failed else 1


def main() -> int:
    """解析发布检查参数。"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    parser = argparse.ArgumentParser(description="执行 ZYW 的 AI 小助理 v0.5 发布验收")
    parser.add_argument(
        "--with-evaluation",
        action="store_true",
        help="运行会产生真实模型费用的 35 题评测；执行前需启动后端并导入标准文档",
    )
    parser.add_argument(
        "--with-e2e",
        action="store_true",
        help="运行需要浏览器及对应测试环境的 Playwright 端到端测试",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "output/release" / f"release-check-{timestamp}.json",
        help="发布报告保存位置",
    )
    args = parser.parse_args()
    return run_release_check(
        with_evaluation=args.with_evaluation,
        with_e2e=args.with_e2e,
        output=args.output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
