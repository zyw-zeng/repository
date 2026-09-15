/** 定义后端公开简历以及聊天资源卡片使用的数据结构。 */

export interface ResumeResource {
  type: "resume";
  title: string;
  description: string;
  filename: string;
  version: string;
  updated_at: string;
  size_bytes: number;
  media_type: "application/pdf";
  download_url: string;
  preview_url: string;
}

export function toResumeProxyUrl(path: string): string {
  /** 将后端公开地址转换为浏览器可用的 Next.js 同源代理地址。 */
  return path.startsWith("/api/v1/")
    ? `/api/backend/${path.slice("/api/v1/".length)}`
    : path;
}
