"use client";

/** 提供避免服务端水合闪烁的浅色、深色主题切换按钮。 */

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  // 服务端快照为 false、浏览器快照为 true，可避免用 Effect 触发额外渲染。
  const mounted = useSyncExternalStore(
    () => () => undefined,
    () => true,
    () => false,
  );

  if (!mounted) return <span aria-hidden="true" className="size-8" />;

  const isDark = resolvedTheme === "dark";
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Button
            aria-label={isDark ? "切换到浅色主题" : "切换到深色主题"}
            variant="ghost"
            size="icon"
            onClick={() => setTheme(isDark ? "light" : "dark")}
          />
        }
      >
        {isDark ? <Sun /> : <Moon />}
      </TooltipTrigger>
      <TooltipContent>{isDark ? "浅色主题" : "深色主题"}</TooltipContent>
    </Tooltip>
  );
}
