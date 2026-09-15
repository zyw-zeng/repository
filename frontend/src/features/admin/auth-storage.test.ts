/** 验证管理员令牌只在标签页会话中保存，并能正确处理过期状态。 */

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  clearAdminToken,
  readAdminToken,
  saveAdminToken,
} from "./auth-storage";

describe("管理员令牌存储", () => {
  afterEach(() => {
    clearAdminToken();
    vi.useRealTimers();
  });

  it("保存并读取仍然有效的令牌", () => {
    vi.setSystemTime(new Date("2026-09-13T00:00:00Z"));
    saveAdminToken({
      access_token: "admin-token",
      token_type: "bearer",
      expires_in: 3600,
    });

    expect(readAdminToken()).toBe("admin-token");
  });

  it("令牌过期后自动清理", () => {
    vi.setSystemTime(new Date("2026-09-13T00:00:00Z"));
    saveAdminToken({
      access_token: "expired-token",
      token_type: "bearer",
      expires_in: 1,
    });
    vi.setSystemTime(new Date("2026-09-13T00:00:02Z"));

    expect(readAdminToken()).toBeUndefined();
    expect(sessionStorage.getItem("zyw_admin_token")).toBeNull();
  });
});
