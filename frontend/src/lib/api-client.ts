/** 封装浏览器通过 Next.js 同源代理访问 FastAPI 的普通 HTTP 请求。 */

import axios from "axios";

export const apiClient = axios.create({
  baseURL: "/api/backend",
  timeout: 60_000,
  headers: { Accept: "application/json" },
});

apiClient.interceptors.request.use((config) => {
  // 管理员令牌仅在当前标签页会话中保存，并由 FastAPI 对每个受保护请求重新校验。
  if (typeof window !== "undefined") {
    const token = window.sessionStorage.getItem("zyw_admin_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});
