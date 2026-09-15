/** 验证桌面和移动视口都能使用单屏 AI 精灵聊天界面。 */

import { expect, test } from "@playwright/test";

test("访客打开首页即可看到精灵和聊天入口", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "从一个问题开始了解 ZYW" }),
  ).toBeVisible();
  const isMobile = (page.viewportSize()?.width ?? 0) < 768;
  if (isMobile) {
    const spirit = page.getByRole("button", {
      name: "拖动精灵或点击打开换装间",
    });
    await expect(spirit).toBeVisible();
    const spiritBox = await spirit.boundingBox();
    if (spiritBox) {
      await page.mouse.move(
        spiritBox.x + spiritBox.width / 2,
        spiritBox.y + spiritBox.height / 2,
      );
      await page.mouse.down();
      await page.mouse.move(24, spiritBox.y + 100, { steps: 6 });
      await page.mouse.up();
      await expect
        .poll(async () => (await spirit.boundingBox())?.x)
        .toBeLessThan(16);
      await expect
        .poll(() =>
          page.evaluate(() =>
            window.localStorage.getItem("zyw_spirit_position_v2"),
          ),
        )
        .toContain('"side":"left"');
    }
  } else {
    await expect(
      page.getByRole("status").filter({ hasText: "你好呀" }),
    ).toBeVisible();
  }
  await expect(
    page.getByRole("textbox", { name: "向 ZYW 的 AI 小助理提问" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "进入知识库管理端" }),
  ).toHaveAttribute("href", "/admin");
  const shell = await page.getByTestId("assistant-shell").boundingBox();
  const viewport = page.viewportSize();
  expect(shell?.width).toBeGreaterThanOrEqual((viewport?.width ?? 0) - 2);
  await expect(page.getByTestId("assistant-shell")).toHaveAttribute(
    "data-layout",
    isMobile ? "mobile" : "desktop",
  );
  await expect(page).toHaveURL(/\/$/);
});

test("320px 窄屏保持完整高度且操作入口不溢出", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 700 });
  await page.goto("/");

  const shell = page.getByTestId("assistant-shell");
  const shellBox = await shell.boundingBox();
  expect(shellBox?.height).toBeGreaterThanOrEqual(698);
  await expect(page.getByRole("button", { name: "打开历史会话" })).toBeVisible();
  await expect(page.getByRole("link", { name: "进入知识库管理端" })).toBeVisible();
  await expect(page.getByRole("button", { name: "开始新对话" })).toBeVisible();
  await expect(
    page.getByRole("textbox", { name: "向 ZYW 的 AI 小助理提问" }),
  ).toBeVisible();

  const footerBox = await page.locator("footer").boundingBox();
  expect((footerBox?.y ?? 0) + (footerBox?.height ?? 0)).toBeGreaterThan(680);
});
