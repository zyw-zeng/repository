"use client";

/** 提供只向 FastAPI 提交管理员密码的登录表单。 */

import { KeyRound, LoaderCircle, LockKeyhole } from "lucide-react";
import { useState } from "react";

import { BrandMark } from "@/components/brand/brand-mark";
import { Button } from "@/components/ui/button";
import { getApiErrorMessage } from "@/features/admin/api-error";
import { saveAdminToken } from "@/features/admin/auth-storage";
import type { AdminToken } from "@/features/admin/types";
import { apiClient } from "@/lib/api-client";

import type { FormEvent } from "react";

export function AdminLogin({
  onAuthenticated,
}: {
  onAuthenticated: () => void;
}) {
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!password || isSubmitting) return;
    setIsSubmitting(true);
    setError(undefined);
    try {
      const response = await apiClient.post<AdminToken>("/auth/login", {
        password,
      });
      saveAdminToken(response.data);
      setPassword("");
      onAuthenticated();
    } catch (requestError) {
      setError(
        getApiErrorMessage(requestError, "登录失败，请检查管理员密码。"),
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="subtle-grid grid min-h-dvh place-items-center px-4 py-10">
      <section className="glass-panel w-full max-w-md rounded-3xl p-6 sm:p-8">
        <div className="mb-8 flex items-center gap-3">
          <BrandMark className="size-11" />
          <div>
            <h1 className="text-xl font-semibold">管理 ZYW 的知识库</h1>
            <p className="text-muted-foreground mt-1 text-sm">
              登录后才能管理文档和索引任务
            </p>
          </div>
        </div>
        <div className="bg-primary/8 text-primary mb-6 flex items-start gap-3 rounded-2xl p-4 text-sm leading-6">
          <LockKeyhole className="mt-0.5 size-4 shrink-0" />
          密码只发送到当前配置的 FastAPI，不会保存在浏览器中。
        </div>
        <form onSubmit={submit} className="space-y-4">
          <label className="block">
            <span className="mb-2 block text-sm font-medium">管理员密码</span>
            <div className="focus-within:border-primary/55 focus-within:ring-primary/10 bg-background/65 flex items-center gap-2 rounded-xl border px-3 focus-within:ring-3">
              <KeyRound className="text-muted-foreground size-4" />
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="输入 .env 中配置的 ADMIN_PASSWORD"
                className="h-11 min-w-0 flex-1 bg-transparent text-sm outline-none"
              />
            </div>
          </label>
          {error && (
            <p role="alert" className="text-destructive text-sm">
              {error}
            </p>
          )}
          <Button
            type="submit"
            size="lg"
            className="w-full"
            disabled={!password || isSubmitting}
          >
            {isSubmitting ? (
              <LoaderCircle className="animate-spin" />
            ) : (
              <LockKeyhole />
            )}
            {isSubmitting ? "正在验证…" : "进入管理端"}
          </Button>
        </form>
      </section>
    </main>
  );
}
