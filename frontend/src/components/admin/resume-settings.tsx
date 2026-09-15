"use client";

/** 管理当前公开简历的预览、下载、版本信息和安全替换。 */

import { Download, ExternalLink, FileCheck2, LoaderCircle, Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/components/ui/button";
import { getApiErrorMessage, isUnauthorized } from "@/features/admin/api-error";
import type { ResumeResource } from "@/features/resume/types";
import { toResumeProxyUrl } from "@/features/resume/types";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";

function formatBytes(bytes: number): string {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function ResumeSettings({ onUnauthorized }: { onUnauthorized: () => void }) {
  const [resource, setResource] = useState<ResumeResource>();
  const [title, setTitle] = useState("曾有为｜AI Agent 应用开发");
  const [version, setVersion] = useState("2026.09");
  const [file, setFile] = useState<File>();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.get<ResumeResource>("/resume");
      setResource(response.data);
      setTitle(response.data.title);
      setVersion(response.data.version);
    } catch (error) {
      if (isUnauthorized(error)) onUnauthorized();
      else toast.error(getApiErrorMessage(error, "当前简历信息读取失败。"));
    } finally {
      setLoading(false);
    }
  }, [onUnauthorized]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function replaceResume() {
    if (!file || !title.trim() || !version.trim() || saving) return;
    const form = new FormData();
    form.append("file", file);
    form.append("title", title.trim());
    form.append("version", version.trim());
    setSaving(true);
    try {
      const response = await apiClient.put<ResumeResource>("/resume", form);
      setResource(response.data);
      setFile(undefined);
      if (inputRef.current) inputRef.current.value = "";
      toast.success("公开简历已经更新，访客端立即生效。");
    } catch (error) {
      if (isUnauthorized(error)) onUnauthorized();
      else toast.error(getApiErrorMessage(error, "简历替换失败，原版本保持不变。"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_24rem]">
      <section className="admin-panel rounded-3xl p-5 sm:p-6">
        <div className="flex items-start gap-4">
          <span className="bg-primary/10 text-primary grid size-12 place-items-center rounded-2xl">
            <FileCheck2 className="size-5" />
          </span>
          <div className="min-w-0">
            <h2 className="font-semibold">当前公开简历</h2>
            <p className="text-muted-foreground mt-1 text-sm">
              访客下载入口和 Agent 简历工具均使用这个版本。
            </p>
          </div>
        </div>
        {loading ? (
          <div className="text-muted-foreground flex items-center gap-2 py-16 text-sm">
            <LoaderCircle className="size-4 animate-spin" /> 正在读取简历信息…
          </div>
        ) : resource ? (
          <div className="mt-6 rounded-2xl border bg-background/60 p-5">
            <p className="text-lg font-semibold">{resource.title}</p>
            <p className="text-muted-foreground mt-2 text-sm">{resource.description}</p>
            <div className="text-muted-foreground mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs">
              <span>版本 {resource.version}</span>
              <span>{formatBytes(resource.size_bytes)}</span>
              <span>{new Date(resource.updated_at).toLocaleString("zh-CN")}</span>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <a
                href={toResumeProxyUrl(resource.preview_url)}
                target="_blank"
                rel="noreferrer"
                className={cn(buttonVariants({ variant: "outline" }))}
              >
                <ExternalLink /> 在线预览
              </a>
              <a
                href={toResumeProxyUrl(resource.download_url)}
                download={resource.filename}
                className={cn(buttonVariants({ variant: "outline" }))}
              >
                <Download /> 下载当前版本
              </a>
            </div>
          </div>
        ) : (
          <p className="text-muted-foreground py-16 text-sm">当前没有可用简历。</p>
        )}
      </section>

      <section className="admin-panel rounded-3xl p-5 sm:p-6">
        <h2 className="font-semibold">上传新版本</h2>
        <p className="text-muted-foreground mt-1 text-sm leading-6">
          新文件通过校验后才会替换当前 PDF。
        </p>
        <div className="mt-5 space-y-4">
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium">展示标题</span>
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              className="admin-input h-11 w-full rounded-xl px-3 text-sm outline-none"
            />
          </label>
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium">版本号</span>
            <input
              value={version}
              onChange={(event) => setVersion(event.target.value)}
              placeholder="例如 2026.09"
              className="admin-input h-11 w-full rounded-xl px-3 text-sm outline-none"
            />
          </label>
          <label className="border-border hover:border-primary/45 flex cursor-pointer flex-col items-center rounded-2xl border border-dashed bg-background/45 px-4 py-7 text-center transition-colors">
            <Upload className="text-primary size-5" />
            <span className="mt-2 text-sm font-medium">
              {file?.name ?? "选择 PDF 简历"}
            </span>
            <span className="text-muted-foreground mt-1 text-xs">最大 10 MB</span>
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf,.pdf"
              className="sr-only"
              onChange={(event) => setFile(event.target.files?.[0])}
            />
          </label>
          <Button
            className="w-full"
            size="lg"
            disabled={!file || !title.trim() || !version.trim() || saving}
            onClick={() => void replaceResume()}
          >
            {saving ? <LoaderCircle className="animate-spin" /> : <Upload />}
            {saving ? "正在安全替换…" : "发布新版本"}
          </Button>
        </div>
      </section>
    </div>
  );
}
