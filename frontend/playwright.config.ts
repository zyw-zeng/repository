/** 使用真实 Next.js 开发服务器执行关键访客路径的端到端测试。 */

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  reporter: "html",
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry",
  },
  projects: [
    // 本地优先复用已安装 Chrome，避免首次验证额外下载大型浏览器包。
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], channel: "chrome" },
    },
    // 覆盖常见的 2K 超宽工作区，防止页面再次被固定最大宽度压窄。
    {
      name: "wide-screen",
      use: {
        ...devices["Desktop Chrome"],
        channel: "chrome",
        viewport: { width: 2560, height: 1271 },
      },
    },
    { name: "mobile", use: { ...devices["Pixel 7"], channel: "chrome" } },
  ],
  webServer: {
    command: "pnpm dev",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
