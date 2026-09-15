"use client";

/** 按后台导航拆分总览、文档、任务、声音和简历管理内容。 */

import {
  CloudUpload,
  Eye,
  EyeOff,
  FileText,
  LoaderCircle,
  RefreshCw,
  RotateCcw,
  Search,
  ShieldCheck,
  Trash2,
  TriangleAlert,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { getApiErrorMessage, isUnauthorized } from "@/features/admin/api-error";
import type {
  DocumentAccepted,
  DocumentItem,
  DocumentList,
  IngestionJob,
  IngestionJobList,
} from "@/features/admin/types";
import { apiClient } from "@/lib/api-client";

import type { AdminSection } from "./admin-sidebar";
import { ConfirmDialog } from "./confirm-dialog";
import { ResumeSettings } from "./resume-settings";
import { VoiceSettings } from "./voice-settings";

const terminalJobStatuses = new Set(["completed", "failed"]);
const statusLabels: Record<string, string> = {
  pending: "等待处理",
  parsing: "正在解析",
  chunking: "正在切分",
  embedding: "正在向量化",
  ready: "可用",
  completed: "已完成",
  failed: "失败",
  deleting: "正在删除",
};
const operationLabels: Record<string, string> = {
  index: "文档入库",
  reindex: "重新索引",
  delete: "删除文档",
};

function statusLabel(status: string): string {
  return statusLabels[status] ?? status;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString("zh-CN");
}

function StatusBadge({ status }: { status: string }) {
  const tone =
    status === "failed"
      ? "border-destructive/35 bg-destructive/8 text-destructive"
      : status === "ready" || status === "completed"
        ? "border-emerald-500/35 bg-emerald-500/8 text-emerald-700 dark:text-emerald-300"
        : "border-amber-500/35 bg-amber-500/8 text-amber-700 dark:text-amber-300";
  return (
    <Badge variant="outline" className={tone}>
      {statusLabel(status)}
    </Badge>
  );
}

function JobCard({
  job,
  documentName,
}: {
  job: IngestionJob;
  documentName?: string;
}) {
  return (
    <article className="admin-card rounded-2xl p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium">
            {operationLabels[job.operation] ?? job.operation}
          </p>
          <p className="text-muted-foreground mt-1 truncate text-xs">
            {documentName ?? job.document_id ?? "文档已经删除"}
          </p>
        </div>
        <StatusBadge status={job.status} />
      </div>
      <div className="bg-muted mt-4 h-2 overflow-hidden rounded-full">
        <div
          className="from-brand-cyan to-primary h-full rounded-full bg-gradient-to-r transition-[width]"
          style={{ width: `${Math.round(job.progress * 100)}%` }}
        />
      </div>
      <div className="text-muted-foreground mt-2 flex justify-between text-xs">
        <span>{Math.round(job.progress * 100)}%</span>
        <span>
          尝试 {job.attempts} 次 · 目标 v{job.target_index_version}
        </span>
      </div>
      <p className="text-muted-foreground mt-2 text-xs">
        {formatDate(job.created_at)}
      </p>
      {job.error_message && (
        <div className="bg-destructive/8 text-destructive mt-3 rounded-xl p-3 text-xs leading-5">
          {job.error_message}
        </div>
      )}
    </article>
  );
}

export function DocumentDashboard({
  activeSection,
  onUnauthorized,
}: {
  activeSection: AdminSection;
  onUnauthorized: () => void;
}) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [jobs, setJobs] = useState<Record<string, IngestionJob>>({});
  const [selectedDocument, setSelectedDocument] = useState<DocumentItem>();
  const [pendingDelete, setPendingDelete] = useState<DocumentItem>();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [visibilityFilter, setVisibilityFilter] = useState("all");
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [busyDocumentId, setBusyDocumentId] = useState<string>();
  const fileInput = useRef<HTMLInputElement | null>(null);

  const handleRequestError = useCallback(
    (error: unknown, fallback: string) => {
      if (isUnauthorized(error)) {
        toast.error("登录状态已失效，请重新登录。");
        onUnauthorized();
        return;
      }
      toast.error(getApiErrorMessage(error, fallback));
    },
    [onUnauthorized],
  );

  const loadDocuments = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get<DocumentList>("/documents", {
        params: { offset: 0, limit: 100 },
      });
      setDocuments(response.data.items);
      setSelectedDocument((current) =>
        current
          ? response.data.items.find((item) => item.id === current.id)
          : undefined,
      );
    } catch (error) {
      handleRequestError(error, "文档列表加载失败。");
    } finally {
      setIsLoading(false);
    }
  }, [handleRequestError]);

  const loadJobs = useCallback(async () => {
    try {
      const response = await apiClient.get<IngestionJobList>(
        "/ingestion-jobs",
        { params: { offset: 0, limit: 100 } },
      );
      setJobs(
        Object.fromEntries(response.data.items.map((job) => [job.id, job])),
      );
    } catch (error) {
      if (isUnauthorized(error)) onUnauthorized();
    }
  }, [onUnauthorized]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadDocuments();
      void loadJobs();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadDocuments, loadJobs]);

  const activeJobIds = useMemo(
    () =>
      Object.values(jobs)
        .filter((job) => !terminalJobStatuses.has(job.status))
        .map((job) => job.id),
    [jobs],
  );

  useEffect(() => {
    if (!activeJobIds.length) return;
    let disposed = false;
    async function poll() {
      const results = await Promise.allSettled(
        activeJobIds.map((id) =>
          apiClient.get<IngestionJob>(`/ingestion-jobs/${id}`),
        ),
      );
      if (disposed) return;
      let completed = false;
      setJobs((current) => {
        const next = { ...current };
        for (const result of results) {
          if (result.status === "fulfilled") {
            next[result.value.data.id] = result.value.data;
            completed ||= terminalJobStatuses.has(result.value.data.status);
          }
        }
        return next;
      });
      if (completed) void loadDocuments();
    }
    const first = window.setTimeout(() => void poll(), 300);
    const interval = window.setInterval(() => void poll(), 1500);
    return () => {
      disposed = true;
      window.clearTimeout(first);
      window.clearInterval(interval);
    };
  }, [activeJobIds, loadDocuments]);

  function trackAccepted(response: DocumentAccepted) {
    setDocuments((current) => [
      response.document,
      ...current.filter((item) => item.id !== response.document.id),
    ]);
    setJobs((current) => ({ ...current, [response.job.id]: response.job }));
  }

  async function uploadDocuments(files: File[]) {
    if (!files.length || isUploading) return;
    setIsUploading(true);
    let succeeded = 0;
    try {
      for (const file of files) {
        const form = new FormData();
        form.append("file", file);
        try {
          const response = await apiClient.post<DocumentAccepted>(
            "/documents",
            form,
          );
          trackAccepted(response.data);
          succeeded += 1;
        } catch (error) {
          handleRequestError(error, `《${file.name}》上传失败。`);
        }
      }
      if (succeeded) toast.success(`${succeeded} 个文件已进入后台处理队列。`);
    } finally {
      setIsUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function updateVisibility(document: DocumentItem) {
    const visibility = document.visibility === "public" ? "private" : "public";
    setBusyDocumentId(document.id);
    try {
      const response = await apiClient.patch<DocumentItem>(
        `/documents/${document.id}/visibility`,
        { visibility },
      );
      setDocuments((current) =>
        current.map((item) => (item.id === document.id ? response.data : item)),
      );
      setSelectedDocument((current) =>
        current?.id === document.id ? response.data : current,
      );
      toast.success(
        visibility === "public" ? "文档已允许访客检索。" : "文档已设为私有。",
      );
    } catch (error) {
      handleRequestError(error, "公开范围修改失败。");
    } finally {
      setBusyDocumentId(undefined);
    }
  }

  async function reindexDocument(document: DocumentItem) {
    setBusyDocumentId(document.id);
    try {
      const response = await apiClient.post<DocumentAccepted>(
        `/documents/${document.id}/reindex`,
      );
      trackAccepted(response.data);
      toast.success("重新索引任务已创建。");
    } catch (error) {
      handleRequestError(error, "重新索引失败。");
    } finally {
      setBusyDocumentId(undefined);
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    setBusyDocumentId(pendingDelete.id);
    try {
      const response = await apiClient.delete<DocumentAccepted>(
        `/documents/${pendingDelete.id}`,
      );
      trackAccepted(response.data);
      setSelectedDocument(undefined);
      setPendingDelete(undefined);
      toast.success("删除任务已创建。");
    } catch (error) {
      handleRequestError(error, "文档删除失败。");
    } finally {
      setBusyDocumentId(undefined);
    }
  }

  const filteredDocuments = documents.filter((document) => {
    const matchesSearch = document.filename
      .toLowerCase()
      .includes(search.trim().toLowerCase());
    const matchesStatus =
      statusFilter === "all" || document.status === statusFilter;
    const matchesVisibility =
      visibilityFilter === "all" || document.visibility === visibilityFilter;
    return matchesSearch && matchesStatus && matchesVisibility;
  });
  const sortedJobs = Object.values(jobs).sort((a, b) =>
    b.created_at.localeCompare(a.created_at),
  );
  const documentNames = Object.fromEntries(
    documents.map((document) => [document.id, document.filename]),
  );
  const publicCount = documents.filter(
    (item) => item.visibility === "public",
  ).length;
  const failedCount = documents.filter((item) => item.status === "failed").length;
  const statistics: Array<{
    label: string;
    value: number;
    icon: LucideIcon;
    tone: string;
  }> = [
    {
      label: "文档总数",
      value: documents.length,
      icon: FileText,
      tone: "text-primary bg-primary/10",
    },
    {
      label: "访客可见",
      value: publicCount,
      icon: Eye,
      tone: "text-emerald-600 bg-emerald-500/10",
    },
    {
      label: "执行中任务",
      value: activeJobIds.length,
      icon: LoaderCircle,
      tone: "text-amber-600 bg-amber-500/10",
    },
    {
      label: "异常文档",
      value: failedCount,
      icon: TriangleAlert,
      tone: "text-destructive bg-destructive/10",
    },
  ];

  function documentActions(document: DocumentItem) {
    const busy = busyDocumentId === document.id;
    return (
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label={`${document.visibility === "public" ? "设为私有" : "设为公开"}：${document.filename}`}
          disabled={busy}
          onClick={() => void updateVisibility(document)}
        >
          {document.visibility === "public" ? <EyeOff /> : <Eye />}
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label={`重新索引：${document.filename}`}
          disabled={busy}
          onClick={() => void reindexDocument(document)}
        >
          <RotateCcw />
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          className="text-destructive"
          aria-label={`删除：${document.filename}`}
          disabled={busy}
          onClick={() => setPendingDelete(document)}
        >
          <Trash2 />
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[100rem] p-4 sm:p-6 lg:p-8">
      {activeSection === "overview" && (
        <div className="space-y-6">
          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {statistics.map(({ label, value, icon: Icon, tone }) => (
              <article key={label} className="admin-panel rounded-2xl p-5">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground text-sm">{label}</span>
                  <span
                    className={`grid size-9 place-items-center rounded-xl ${tone}`}
                  >
                    <Icon
                      className={
                        label === "执行中任务" && value
                          ? "size-4 animate-spin"
                          : "size-4"
                      }
                    />
                  </span>
                </div>
                <p className="mt-5 text-3xl font-semibold tracking-tight">
                  {value}
                </p>
              </article>
            ))}
          </section>
          <section className="grid gap-5 xl:grid-cols-2">
            <div className="admin-panel rounded-3xl p-5">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2 className="font-semibold">最近文档</h2>
                  <p className="text-muted-foreground mt-1 text-xs">
                    知识库最近更新内容
                  </p>
                </div>
                <ShieldCheck className="text-primary size-5" />
              </div>
              <div className="space-y-2">
                {documents.slice(0, 5).map((document) => (
                  <button
                    key={document.id}
                    onClick={() => setSelectedDocument(document)}
                    className="admin-card flex w-full items-center justify-between gap-3 rounded-xl p-3 text-left"
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium">
                        {document.filename}
                      </span>
                      <span className="text-muted-foreground mt-1 block text-xs">
                        {document.chunk_count} 个切片 · v
                        {document.active_index_version}
                      </span>
                    </span>
                    <StatusBadge status={document.status} />
                  </button>
                ))}
                {!documents.length && (
                  <p className="text-muted-foreground py-10 text-center text-sm">
                    还没有文档。
                  </p>
                )}
              </div>
            </div>
            <div className="admin-panel rounded-3xl p-5">
              <div className="mb-4">
                <h2 className="font-semibold">最近任务</h2>
                <p className="text-muted-foreground mt-1 text-xs">
                  任务进度会自动刷新
                </p>
              </div>
              <div className="space-y-3">
                {sortedJobs.slice(0, 3).map((job) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    documentName={
                      job.document_id
                        ? documentNames[job.document_id]
                        : undefined
                    }
                  />
                ))}
                {!sortedJobs.length && (
                  <p className="text-muted-foreground py-10 text-center text-sm">
                    暂无任务记录。
                  </p>
                )}
              </div>
            </div>
          </section>
        </div>
      )}

      {activeSection === "documents" && (
        <div className="space-y-5">
          <section
            className={`admin-panel rounded-3xl border-2 border-dashed p-6 transition-colors ${
              isDragging ? "border-primary bg-primary/5" : "border-border"
            }`}
            onDragOver={(event) => {
              event.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setIsDragging(false);
              void uploadDocuments(Array.from(event.dataTransfer.files));
            }}
          >
            <div className="flex flex-col items-center justify-between gap-4 text-center sm:flex-row sm:text-left">
              <div className="flex items-center gap-4">
                <span className="bg-primary/10 text-primary grid size-12 place-items-center rounded-2xl">
                  <CloudUpload />
                </span>
                <div>
                  <h2 className="font-semibold">上传知识文档</h2>
                  <p className="text-muted-foreground mt-1 text-sm">
                    拖入或选择 PDF、DOCX、Markdown、TXT，可一次选择多个文件。
                  </p>
                </div>
              </div>
              <input
                ref={fileInput}
                id="admin-document-upload"
                type="file"
                multiple
                accept=".pdf,.md,.markdown,.txt,.docx"
                className="sr-only"
                onChange={(event) =>
                  void uploadDocuments(Array.from(event.target.files ?? []))
                }
              />
              <Button
                render={<label htmlFor="admin-document-upload" />}
                disabled={isUploading}
              >
                {isUploading ? (
                  <LoaderCircle className="animate-spin" />
                ) : (
                  <CloudUpload />
                )}
                {isUploading ? "正在上传…" : "选择文件"}
              </Button>
            </div>
          </section>
          <section className="admin-panel overflow-hidden rounded-3xl">
            <div className="grid gap-3 border-b p-4 md:grid-cols-[minmax(0,1fr)_10rem_10rem_auto]">
              <label className="admin-input flex items-center gap-2 rounded-xl px-3">
                <Search className="text-muted-foreground size-4" />
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="搜索文件名"
                  aria-label="按文件名搜索"
                  className="h-10 min-w-0 flex-1 bg-transparent text-sm outline-none"
                />
              </label>
              <select
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
                className="admin-input h-10 rounded-xl px-3 text-sm"
              >
                <option value="all">全部状态</option>
                <option value="ready">可用</option>
                <option value="failed">失败</option>
                <option value="pending">处理中</option>
              </select>
              <select
                value={visibilityFilter}
                onChange={(event) => setVisibilityFilter(event.target.value)}
                className="admin-input h-10 rounded-xl px-3 text-sm"
              >
                <option value="all">全部范围</option>
                <option value="public">公开</option>
                <option value="private">私有</option>
              </select>
              <Button
                variant="outline"
                size="icon"
                aria-label="刷新文档列表"
                onClick={() => void loadDocuments()}
                disabled={isLoading}
              >
                <RefreshCw className={isLoading ? "animate-spin" : ""} />
              </Button>
            </div>
            {isLoading && !documents.length ? (
              <div className="text-muted-foreground flex justify-center gap-2 py-20 text-sm">
                <LoaderCircle className="animate-spin" /> 正在读取文档…
              </div>
            ) : filteredDocuments.length === 0 ? (
              <div className="text-muted-foreground py-20 text-center text-sm">
                没有匹配的文档。
              </div>
            ) : (
              <>
                <div className="hidden overflow-x-auto md:block">
                  <table className="w-full min-w-[760px] text-left text-sm">
                    <thead className="bg-muted/45 text-muted-foreground text-xs">
                      <tr>
                        <th className="px-5 py-3 font-medium">文件</th>
                        <th className="px-4 py-3 font-medium">状态</th>
                        <th className="px-4 py-3 font-medium">可见性</th>
                        <th className="px-4 py-3 font-medium">索引</th>
                        <th className="px-4 py-3 font-medium">操作</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {filteredDocuments.map((document) => (
                        <tr key={document.id} className="hover:bg-muted/25">
                          <td className="px-5 py-4">
                            <button
                              onClick={() => setSelectedDocument(document)}
                              className="max-w-sm text-left"
                            >
                              <span className="block truncate font-medium">
                                {document.filename}
                              </span>
                              <span className="text-muted-foreground mt-1 block text-xs">
                                {formatBytes(document.size_bytes)} ·{" "}
                                {document.chunk_count} 个切片
                              </span>
                            </button>
                          </td>
                          <td className="px-4">
                            <StatusBadge status={document.status} />
                          </td>
                          <td className="px-4">
                            <Badge variant="outline">
                              {document.visibility === "public" ? "公开" : "私有"}
                            </Badge>
                          </td>
                          <td className="px-4">v{document.active_index_version}</td>
                          <td className="px-4">{documentActions(document)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="space-y-3 p-3 md:hidden">
                  {filteredDocuments.map((document) => (
                    <article key={document.id} className="admin-card rounded-2xl p-4">
                      <button
                        onClick={() => setSelectedDocument(document)}
                        className="w-full text-left"
                      >
                        <p className="break-words font-medium">{document.filename}</p>
                        <p className="text-muted-foreground mt-1 text-xs">
                          {formatBytes(document.size_bytes)} · {document.chunk_count}{" "}
                          个切片 · v{document.active_index_version}
                        </p>
                      </button>
                      <div className="mt-3 flex items-center justify-between">
                        <div className="flex gap-2">
                          <StatusBadge status={document.status} />
                          <Badge variant="outline">
                            {document.visibility === "public" ? "公开" : "私有"}
                          </Badge>
                        </div>
                        {documentActions(document)}
                      </div>
                    </article>
                  ))}
                </div>
              </>
            )}
          </section>
        </div>
      )}

      {activeSection === "jobs" && (
        <div className="space-y-5">
          <section className="admin-panel flex items-center justify-between rounded-2xl p-4">
            <div>
              <h2 className="font-semibold">持久化任务中心</h2>
              <p className="text-muted-foreground mt-1 text-sm">
                刷新页面后仍可查看处理进度、尝试次数和失败原因。
              </p>
            </div>
            <Button
              variant="outline"
              size="icon"
              aria-label="刷新任务"
              onClick={() => void loadJobs()}
            >
              <RefreshCw />
            </Button>
          </section>
          <section className="grid gap-4 lg:grid-cols-2 2xl:grid-cols-3">
            {sortedJobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                documentName={
                  job.document_id ? documentNames[job.document_id] : undefined
                }
              />
            ))}
            {!sortedJobs.length && (
              <div className="admin-panel text-muted-foreground col-span-full rounded-3xl py-24 text-center text-sm">
                暂无任务记录。
              </div>
            )}
          </section>
        </div>
      )}

      {activeSection === "voices" && (
        <VoiceSettings onUnauthorized={onUnauthorized} />
      )}
      {activeSection === "resume" && (
        <ResumeSettings onUnauthorized={onUnauthorized} />
      )}

      <Sheet
        open={Boolean(selectedDocument)}
        onOpenChange={(open) => !open && setSelectedDocument(undefined)}
      >
        <SheetContent
          side="right"
          className="w-[94vw] overflow-y-auto sm:max-w-lg"
        >
          {selectedDocument && (
            <>
              <SheetHeader className="border-b p-5">
                <SheetTitle className="pr-8">
                  {selectedDocument.filename}
                </SheetTitle>
                <SheetDescription>文档详情和当前活动索引信息</SheetDescription>
              </SheetHeader>
              <div className="space-y-5 p-5">
                <div className="grid grid-cols-2 gap-3">
                  {[
                    ["状态", statusLabel(selectedDocument.status)],
                    [
                      "公开范围",
                      selectedDocument.visibility === "public" ? "公开" : "私有",
                    ],
                    ["文件类型", selectedDocument.file_type.toUpperCase()],
                    ["文件大小", formatBytes(selectedDocument.size_bytes)],
                    ["切片数量", selectedDocument.chunk_count],
                    ["活动索引", `v${selectedDocument.active_index_version}`],
                  ].map(([label, value]) => (
                    <div key={String(label)} className="admin-card rounded-xl p-3">
                      <p className="text-muted-foreground text-xs">{String(label)}</p>
                      <p className="mt-1 text-sm font-medium">{String(value)}</p>
                    </div>
                  ))}
                </div>
                <div className="text-muted-foreground space-y-2 text-sm">
                  <p>创建：{formatDate(selectedDocument.created_at)}</p>
                  <p>更新：{formatDate(selectedDocument.updated_at)}</p>
                  <p className="break-all">ID：{selectedDocument.id}</p>
                </div>
                {selectedDocument.error_message && (
                  <div className="bg-destructive/8 text-destructive rounded-xl p-3 text-sm">
                    {selectedDocument.error_message}
                  </div>
                )}
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    onClick={() => void updateVisibility(selectedDocument)}
                  >
                    {selectedDocument.visibility === "public" ? <EyeOff /> : <Eye />}
                    {selectedDocument.visibility === "public"
                      ? "设为私有"
                      : "设为公开"}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => void reindexDocument(selectedDocument)}
                  >
                    <RotateCcw /> 重新索引
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={() => setPendingDelete(selectedDocument)}
                  >
                    <Trash2 /> 删除文档
                  </Button>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="删除这份文档？"
        description={`《${pendingDelete?.filename ?? ""}》及其向量索引将进入删除任务。该操作完成后无法恢复。`}
        busy={Boolean(pendingDelete && busyDocumentId === pendingDelete.id)}
        onCancel={() => setPendingDelete(undefined)}
        onConfirm={() => void confirmDelete()}
      />
    </div>
  );
}
