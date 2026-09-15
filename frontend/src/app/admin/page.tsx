import type { Metadata } from "next";

import { AdminShell } from "@/components/admin/admin-shell";

export const metadata: Metadata = {
  title: "ZYW 管理中心",
  description: "管理知识文档、处理任务、角色声音与公开简历。",
  robots: { index: false, follow: false },
};

export default function AdminPage() {
  return <AdminShell />;
}
