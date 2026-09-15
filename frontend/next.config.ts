import type { NextConfig } from "next";

// 只在 Next.js 服务端读取 FastAPI 地址，避免把内部部署地址打包进浏览器。
const fastApiBaseUrl = (
  process.env.FASTAPI_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

const nextConfig: NextConfig = {
  poweredByHeader: false,
  // 允许本机自动化测试从 127.0.0.1 访问开发资源。
  allowedDevOrigins: ["127.0.0.1"],
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${fastApiBaseUrl}/api/v1/:path*`,
      },
      {
        source: "/api/system/:path*",
        destination: `${fastApiBaseUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
