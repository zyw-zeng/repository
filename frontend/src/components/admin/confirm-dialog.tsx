"use client";

/** 使用统一品牌样式确认危险操作，替代浏览器原生确认框。 */

import { TriangleAlert } from "lucide-react";

import { Button } from "@/components/ui/button";

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "确认删除",
  busy = false,
  onCancel,
  onConfirm,
}: {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  busy?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-60 grid place-items-center bg-slate-950/55 p-4 backdrop-blur-sm">
      <section
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="admin-confirm-title"
        className="bg-popover text-popover-foreground w-full max-w-md rounded-3xl border p-6 shadow-2xl"
      >
        <span className="bg-destructive/10 text-destructive grid size-11 place-items-center rounded-2xl">
          <TriangleAlert className="size-5" />
        </span>
        <h2 id="admin-confirm-title" className="mt-4 text-lg font-semibold">
          {title}
        </h2>
        <p className="text-muted-foreground mt-2 text-sm leading-6">{description}</p>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" onClick={onCancel} disabled={busy}>
            取消
          </Button>
          <Button variant="destructive" onClick={onConfirm} disabled={busy}>
            {busy ? "正在处理…" : confirmLabel}
          </Button>
        </div>
      </section>
    </div>
  );
}
