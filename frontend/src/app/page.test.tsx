/** 验证单屏双栏界面的精灵、聊天入口和推荐问题不会丢失。 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import HomePage from "./page";
import { apiClient } from "@/lib/api-client";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("首页", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        suggestions: ["介绍一下 ZYW 的技术能力"],
        source: "generated",
      },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("同时展示 AI 精灵和聊天区域", async () => {
    render(<HomePage />);

    expect(screen.getByRole("status")).toHaveTextContent(
      "你好呀，想了解 ZYW 的什么？",
    );
    expect(
      screen.getByRole("heading", { name: "从一个问题开始了解 ZYW" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("textbox", { name: "向 ZYW 的 AI 小助理提问" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("button", { name: "介绍一下 ZYW 的技术能力" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("assistant-shell")).toHaveAttribute(
      "data-layout",
      "desktop",
    );
    expect(
      screen.getByRole("link", { name: "下载曾有为的简历" }),
    ).toHaveAttribute("href", "/api/backend/resume/download");
  });

  it("窄屏只挂载独立移动端工作区", () => {
    vi.spyOn(window, "matchMedia").mockImplementation(
      (query) =>
        ({
          matches: query === "(max-width: 767px)",
          media: query,
          onchange: null,
          addListener: () => undefined,
          removeListener: () => undefined,
          addEventListener: () => undefined,
          removeEventListener: () => undefined,
          dispatchEvent: () => false,
        }) as MediaQueryList,
    );

    render(<HomePage />);

    expect(screen.getByTestId("assistant-shell")).toHaveAttribute(
      "data-layout",
      "mobile",
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "准备好啦，问我关于 ZYW 的事",
    );
    expect(
      screen.getByRole("link", { name: "下载曾有为的简历" }),
    ).toHaveAttribute("href", "/api/backend/resume/download");
  });

  it("桌面精灵可以打开换装间并保存形象", async () => {
    render(<HomePage />);

    await userEvent.click(
      screen.getByRole("button", { name: "打开精灵换装间" }),
    );
    expect(
      await screen.findByRole("heading", { name: /精灵换装间/ }),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /比特/ }));

    expect(screen.getByRole("button", { name: /比特/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(window.localStorage.getItem("zyw_spirit_appearance_v2")).toContain(
      '\"characterId\":\"byte\"',
    );
  });

  it("点击桌面精灵后展示角色快捷问题", async () => {
    render(<HomePage />);

    await userEvent.click(screen.getByRole("button", { name: "和星云互动" }));

    expect(screen.getByText("捕捉到一颗新问题！")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "介绍一下 ZYW" }),
    ).toBeInTheDocument();
  });

  it("在聊天输入区切换 JD 岗位匹配模式", async () => {
    render(<HomePage />);

    await userEvent.click(
      screen.getByRole("button", { name: "进入岗位匹配模式" }),
    );

    expect(screen.getByText("JD 岗位匹配模式")).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("粘贴完整岗位职责、任职要求和加分项…"),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "打开 JD 岗位匹配" }),
    ).not.toBeInTheDocument();
  });
});
