"""把项目说明文档导入知识库，并等待后台索引任务完成。"""

import argparse
import time
from pathlib import Path

import httpx

from app.core.config import get_settings


def main() -> int:
    """上传固定题集依赖的资料，重复文档视为已经准备完成。"""
    parser = argparse.ArgumentParser(description="准备可靠 RAG 标准评测资料")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    arguments = parser.parse_args()
    jobs: list[str] = []
    document_ids: set[str] = set()
    settings = get_settings()
    if not settings.admin_password:
        print("未配置 ADMIN_PASSWORD，无法准备受保护的评测资料。")
        return 1

    with httpx.Client(base_url=arguments.base_url.rstrip("/"), timeout=180) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"password": settings.admin_password},
        )
        login.raise_for_status()
        client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

        for filename in ("README.md", "DEVELOPMENT_PLAN.md", "docs/MODEL_DECISION.md"):
            path = Path(filename)
            response = client.post(
                "/api/v1/documents",
                files={"file": (path.name, path.read_bytes(), "text/markdown")},
            )
            if response.status_code == 409:
                continue
            response.raise_for_status()
            payload = response.json()
            jobs.append(payload["job"]["id"])
            document_ids.add(payload["document"]["id"])

        deadline = time.monotonic() + 240
        states: dict[str, str] = {}
        while jobs and time.monotonic() < deadline:
            states = {
                job_id: client.get(f"/api/v1/ingestion-jobs/{job_id}").json()["status"]
                for job_id in jobs
            }
            if all(state in {"completed", "failed"} for state in states.values()):
                break
            time.sleep(2)

        # 重复上传的评测文档也可能来自历史迁移，需要一并显式设为公开。
        listing = client.get("/api/v1/documents", params={"limit": 100})
        listing.raise_for_status()
        expected_names = {"README.md", "DEVELOPMENT_PLAN.md", "MODEL_DECISION.md"}
        document_ids.update(
            item["id"]
            for item in listing.json()["items"]
            if item["filename"] in expected_names
        )
        for document_id in document_ids:
            visibility = client.patch(
                f"/api/v1/documents/{document_id}/visibility",
                json={"visibility": "public"},
            )
            visibility.raise_for_status()

    print(f"评测资料任务状态：{states or '文档已存在'}")
    return 0 if all(state == "completed" for state in states.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
