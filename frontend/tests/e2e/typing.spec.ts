/** 验证正式回答通过 SSE 片段逐步显示。 */

import { expect, test } from "@playwright/test";

test("正式回答通过 SSE 呈现打字机效果", async ({ page }) => {
  const answer =
    "这是通过 SSE 逐步显示的正式回答，用于确认浏览器不会把所有文字一次性展示出来。".repeat(
      4,
    );
  const conversation = {
    id: "typing-conversation",
    title: "打字机测试",
    messages: [],
    created_at: "2026-09-13T00:00:00Z",
    updated_at: "2026-09-13T00:00:00Z",
  };

  await page.route("**/api/backend/conversations", async (route) => {
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify(conversation),
    });
  });
  await page.route(
    "**/api/backend/conversations/*/messages/stream",
    async (route) => {
      const body = [
        'event: run_started\ndata: {"request_id":"typing-request"}',
        `event: answer_delta\ndata: ${JSON.stringify({ delta: answer })}`,
        `event: answer_final\ndata: ${JSON.stringify({ answer })}`,
        "event: citations\ndata: []",
        'event: completed\ndata: {"grounded":false,"degraded":false,"duration_ms":100}',
        "",
      ].join("\n\n");
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body,
      });
    },
  );

  await page.goto("/");
  await page.getByRole("button", { name: "介绍一下 ZYW 的技术能力" }).click();

  const assistantMessage = page.locator("article").filter({ hasText: answer });
  await expect(assistantMessage).toBeVisible();
  await expect(assistantMessage).toContainText(answer);
});
