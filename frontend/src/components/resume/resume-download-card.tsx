/** 在聊天回答中展示可预览、可下载的简历资源卡片。 */

import { Download, ExternalLink, FileText } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import {
  type ResumeResource,
  toResumeProxyUrl,
} from "@/features/resume/types";
import { cn } from "@/lib/utils";

function formatFileSize(size: number): string {
  if (!Number.isFinite(size) || size <= 0) return "PDF";
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

export function ResumeDownloadCard({ resource }: { resource: ResumeResource }) {
  return (
    <section className="border-border/60 from-primary/8 via-background/65 to-brand-cyan/8 mt-4 overflow-hidden rounded-2xl border bg-gradient-to-br p-4 shadow-sm">
      <div className="flex min-w-0 items-start gap-3">
        <span className="bg-primary/12 text-primary grid size-11 shrink-0 place-items-center rounded-xl">
          <FileText className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate font-semibold">{resource.title}</p>
          <p className="text-muted-foreground mt-1 text-xs leading-5">
            {resource.description}
          </p>
          <p className="text-muted-foreground mt-1 text-[11px]">
            PDF · {formatFileSize(resource.size_bytes)} · 版本 {resource.version}
          </p>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2">
        <a
          href={toResumeProxyUrl(resource.download_url)}
          download={resource.filename}
          className={cn(buttonVariants({ size: "sm" }), "min-w-0")}
        >
          <Download data-icon="inline-start" />
          下载 PDF
        </a>
        <a
          href={toResumeProxyUrl(resource.preview_url)}
          target="_blank"
          rel="noreferrer"
          className={cn(
            buttonVariants({ variant: "outline", size: "sm" }),
            "min-w-0",
          )}
        >
          <ExternalLink data-icon="inline-start" />
          在线查看
        </a>
      </div>
    </section>
  );
}
