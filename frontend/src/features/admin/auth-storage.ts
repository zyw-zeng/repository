/** 管理员令牌仅保存在当前浏览器标签会话中，并记录本地过期时间。 */

import type { AdminToken } from "./types";

const TOKEN_KEY = "zyw_admin_token";
const EXPIRES_AT_KEY = "zyw_admin_token_expires_at";

export function saveAdminToken(token: AdminToken): void {
  window.sessionStorage.setItem(TOKEN_KEY, token.access_token);
  window.sessionStorage.setItem(
    EXPIRES_AT_KEY,
    String(Date.now() + token.expires_in * 1000),
  );
}

export function readAdminToken(): string | undefined {
  if (typeof window === "undefined") return undefined;
  const token = window.sessionStorage.getItem(TOKEN_KEY);
  const expiresAt = Number(window.sessionStorage.getItem(EXPIRES_AT_KEY));
  if (!token || !Number.isFinite(expiresAt) || expiresAt <= Date.now()) {
    clearAdminToken();
    return undefined;
  }
  return token;
}

export function clearAdminToken(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(TOKEN_KEY);
  window.sessionStorage.removeItem(EXPIRES_AT_KEY);
}
