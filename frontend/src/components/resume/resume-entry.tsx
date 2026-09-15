/** 提供桌面端文字入口和移动端紧凑简历下载入口。 */

import { FileDown } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function ResumeEntry({ compact = false }: { compact?: boolean }) {
  return (
    <a
      href="/api/backend/resume/download"
      download
      aria-label="下载曾有为的简历"
      className={cn(
        buttonVariants({ variant: "ghost", size: compact ? "icon" : "sm" }),
      )}
    >
      <FileDown data-icon="inline-start" />
      {!compact && <span>简历</span>}
    </a>
  );
}
