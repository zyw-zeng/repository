"use client";

/** 定义后台导航结构，并为桌面侧栏与移动抽屉复用同一菜单。 */

import {
  BriefcaseBusiness,
  FileText,
  Gauge,
  ListTodo,
  Volume2,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { BrandMark } from "@/components/brand/brand-mark";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type AdminSection =
  | "overview"
  | "documents"
  | "jobs"
  | "voices"
  | "resume";

export const adminSections: Array<{
  id: AdminSection;
  label: string;
  description: string;
  icon: LucideIcon;
}> = [
  { id: "overview", label: "总览", description: "数据与服务状态", icon: Gauge },
  { id: "documents", label: "文档管理", description: "知识内容与公开范围", icon: FileText },
  { id: "jobs", label: "处理任务", description: "入库与索引进度", icon: ListTodo },
  { id: "voices", label: "角色与声音", description: "精灵音色与试听", icon: Volume2 },
  { id: "resume", label: "简历管理", description: "公开简历与版本", icon: BriefcaseBusiness },
];

export function AdminSidebar({
  active,
  onSelect,
}: {
  active: AdminSection;
  onSelect: (section: AdminSection) => void;
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex h-20 items-center gap-3 px-5">
        <BrandMark className="size-10" />
        <div>
          <p className="font-semibold">ZYW 管理中心</p>
          <p className="text-muted-foreground text-xs">AI 小助理控制台</p>
        </div>
      </div>
      <nav className="flex-1 space-y-1.5 px-3 py-3" aria-label="后台管理导航">
        {adminSections.map(({ id, label, description, icon: Icon }) => (
          <Button
            key={id}
            variant="ghost"
            onClick={() => onSelect(id)}
            aria-current={active === id ? "page" : undefined}
            className={cn(
              "h-auto w-full justify-start gap-3 rounded-xl px-3 py-3 text-left",
              active === id &&
                "bg-primary/12 text-primary hover:bg-primary/16 dark:bg-primary/15",
            )}
          >
            <span className="bg-background/70 grid size-9 shrink-0 place-items-center rounded-lg border">
              <Icon className="size-4" />
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-medium">{label}</span>
              <span className="text-muted-foreground mt-0.5 block truncate text-[11px] font-normal">
                {description}
              </span>
            </span>
          </Button>
        ))}
      </nav>
      <div className="border-border/60 border-t p-4">
        <div className="bg-emerald-500/8 text-emerald-700 dark:text-emerald-300 flex items-center gap-2 rounded-xl px-3 py-2.5 text-xs">
          <span className="size-2 rounded-full bg-emerald-500 shadow-[0_0_0.75rem_rgba(16,185,129,0.55)]" />
          管理服务已连接
        </div>
      </div>
    </div>
  );
}
