/** 使用模拟的受保护接口验证管理端登录态、文档和任务信息展示。 */

import { expect, test } from "@playwright/test";

async function mockAdminApis(page: import("@playwright/test").Page) {
  // 仅拦截管理端依赖的后端请求，页面本身仍由真实 Next.js 提供。
  await page.route("**/api/backend/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ authenticated: true }),
    });
  });
  await page.route("**/api/backend/documents?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            id: "document-1",
            filename: "ZYW 项目介绍.pdf",
            file_type: "pdf",
            size_bytes: 2048,
            content_hash: "test-hash",
            status: "ready",
            visibility: "public",
            chunk_count: 12,
            active_index_version: 3,
            error_message: null,
            created_at: "2026-09-13T00:00:00Z",
            updated_at: "2026-09-13T00:10:00Z",
          },
        ],
        total: 1,
        offset: 0,
        limit: 100,
      }),
    });
  });
  await page.route("**/api/backend/ingestion-jobs?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], offset: 0, limit: 100 }),
    });
  });
}

test("管理员可以查看文档、公开范围和索引版本", async ({ page }) => {
  await page.addInitScript(() => {
    sessionStorage.setItem("zyw_admin_token", "e2e-admin-token");
    sessionStorage.setItem(
      "zyw_admin_token_expires_at",
      String(Date.now() + 60 * 60 * 1000),
    );
  });
  await mockAdminApis(page);
  await page.route("**/api/backend/documents", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({
        document: {
          id: "document-2",
          filename: "新资料.txt",
          file_type: "txt",
          status: "pending",
          size_bytes: 12,
          chunk_count: 0,
          active_index_version: 0,
          visibility: "private",
          error_message: null,
          created_at: "2026-09-13T00:20:00Z",
          updated_at: "2026-09-13T00:20:00Z",
        },
        job: {
          id: "job-1",
          document_id: "document-2",
          operation: "index",
          target_index_version: 1,
          status: "pending",
          progress: 0,
          attempts: 0,
          error_message: null,
          started_at: null,
          finished_at: null,
          created_at: "2026-09-13T00:20:00Z",
        },
      }),
    });
  });
  await page.route("**/api/backend/ingestion-jobs/job-1", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "job-1",
        document_id: "document-2",
        operation: "index",
        target_index_version: 1,
        status: "failed",
        progress: 0.45,
        attempts: 2,
        error_message: "测试用解析失败原因",
        started_at: "2026-09-13T00:20:01Z",
        finished_at: "2026-09-13T00:20:02Z",
        created_at: "2026-09-13T00:20:00Z",
      }),
    });
  });
  await page.goto("/admin");

  await expect(
    page.getByRole("heading", { name: "总览" }),
  ).toBeVisible();
  await expect(page.getByText("ZYW 项目介绍.pdf")).toBeVisible();
  await expect(page.getByText("文档总数")).toBeVisible();
  if ((page.viewportSize()?.width ?? 1280) < 1024) {
    await page.getByRole("button", { name: "打开后台导航" }).click();
  }
  await expect(page.getByRole("button", { name: /角色与声音/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /简历管理/ })).toBeVisible();

  await page.getByRole("button", { name: /文档管理/ }).click();
  await expect(
    page.locator('[data-slot="badge"]:visible').filter({ hasText: /^公开$/ }),
  ).toBeVisible();

  await page.locator("#admin-document-upload").setInputFiles({
    name: "新资料.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("ZYW test file"),
  });
  if ((page.viewportSize()?.width ?? 1280) < 1024) {
    await page.getByRole("button", { name: "打开后台导航" }).click();
  }
  await page.getByRole("button", { name: /处理任务/ }).click();
  await expect(page.getByText("文档入库")).toBeVisible();
  await expect(page.getByText("尝试 2 次")).toBeVisible();
  await expect(page.getByText(/目标 v1/)).toBeVisible();
  await expect(page.getByText("测试用解析失败原因")).toBeVisible();
});

test("没有令牌时只显示管理员登录入口", async ({ page }) => {
  await page.goto("/admin");

  await expect(
    page.getByRole("heading", { name: "管理 ZYW 的知识库" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "进入管理端" })).toBeVisible();
});
