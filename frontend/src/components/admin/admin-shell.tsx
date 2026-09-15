"use client";

/** 验证现有令牌并在登录表单与文档控制台之间切换。 */

import { LoaderCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { clearAdminToken, readAdminToken } from "@/features/admin/auth-storage";
import type { AdminAuthState } from "@/features/admin/types";
import { apiClient } from "@/lib/api-client";

import { AdminLogin } from "./admin-login";
import { AdminConsole } from "./admin-console";

export function AdminShell() {
  const [authState, setAuthState] = useState<AdminAuthState>(() =>
    readAdminToken() ? "checking" : "anonymous",
  );

  const verifyToken = useCallback(async () => {
    if (!readAdminToken()) {
      setAuthState("anonymous");
      return;
    }
    try {
      await apiClient.get("/auth/me");
      setAuthState("authenticated");
    } catch {
      clearAdminToken();
      setAuthState("anonymous");
    }
  }, []);

  useEffect(() => {
    if (authState !== "checking") return;
    const timer = window.setTimeout(() => void verifyToken(), 0);
    return () => window.clearTimeout(timer);
  }, [authState, verifyToken]);

  if (authState === "checking") {
    return (
      <main className="grid min-h-dvh place-items-center">
        <div className="text-muted-foreground flex items-center gap-2 text-sm">
          <LoaderCircle className="size-5 animate-spin" /> 正在验证管理权限…
        </div>
      </main>
    );
  }
  if (authState === "anonymous") {
    return <AdminLogin onAuthenticated={() => setAuthState("authenticated")} />;
  }
  return (
    <AdminConsole
      onUnauthorized={() => {
        clearAdminToken();
        setAuthState("anonymous");
      }}
      onLogout={() => {
        clearAdminToken();
        setAuthState("anonymous");
      }}
    />
  );
}
