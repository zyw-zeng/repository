/** 从 Axios 与 FastAPI 统一错误体中提取适合界面显示的中文消息。 */

import axios from "axios";

export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (!axios.isAxiosError(error)) return fallback;
  const data = error.response?.data as
    { error?: { message?: string }; detail?: string } | undefined;
  return data?.error?.message ?? data?.detail ?? fallback;
}

export function isUnauthorized(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 401;
}
