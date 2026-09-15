"use client";

/** 提供桌面侧栏、移动抽屉和页面级标题栏的后台控制台框架。 */

import { ArrowLeft, LogOut, Menu } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent } from "@/components/ui/sheet";

import { AdminSidebar, adminSections, type AdminSection } from "./admin-sidebar";
import { DocumentDashboard } from "./document-dashboard";

export function AdminConsole({
  onUnauthorized,
  onLogout,
}: {
  onUnauthorized: () => void;
  onLogout: () => void;
}) {
  const [activeSection, setActiveSection] = useState<AdminSection>("overview");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const active = adminSections.find((item) => item.id === activeSection)!;

  function selectSection(section: AdminSection) {
    setActiveSection(section);
    setMobileMenuOpen(false);
  }

  return (
    <main className="admin-surface min-h-dvh lg:grid lg:grid-cols-[16rem_minmax(0,1fr)]">
      <aside className="admin-sidebar-surface sticky top-0 hidden h-dvh border-r lg:block">
        <AdminSidebar active={activeSection} onSelect={selectSection} />
      </aside>
      <div className="min-w-0">
        <header className="admin-topbar sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b px-4 backdrop-blur-xl sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              aria-label="打开后台导航"
              onClick={() => setMobileMenuOpen(true)}
            >
              <Menu />
            </Button>
            <div className="min-w-0">
              <h1 className="truncate text-sm font-semibold sm:text-base">{active.label}</h1>
              <p className="text-muted-foreground hidden text-xs sm:block">
                {active.description}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <Button render={<Link href="/" />} variant="ghost" size="sm">
              <ArrowLeft data-icon="inline-start" />
              <span className="hidden sm:inline">返回助理</span>
            </Button>
            <ThemeToggle />
            <Button variant="ghost" size="sm" onClick={onLogout}>
              <LogOut data-icon="inline-start" />
              <span className="hidden sm:inline">退出</span>
            </Button>
          </div>
        </header>
        <DocumentDashboard
          activeSection={activeSection}
          onUnauthorized={onUnauthorized}
        />
      </div>
      <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
        <SheetContent side="left" className="w-[86vw] max-w-xs p-0">
          <AdminSidebar active={activeSection} onSelect={selectSection} />
        </SheetContent>
      </Sheet>
    </main>
  );
}
