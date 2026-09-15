/** 使用纯 CSS 与图标构成品牌标记，避免首屏额外图片请求。 */

import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

export function BrandMark({ className }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "from-brand-cyan via-brand-indigo to-brand-violet shadow-primary/20 relative grid size-9 place-items-center rounded-xl bg-gradient-to-br text-white shadow-lg",
        className,
      )}
    >
      <Sparkles className="size-4" strokeWidth={2.2} />
      <span className="absolute inset-px rounded-[calc(var(--radius)-0.1rem)] ring-1 ring-white/25" />
    </span>
  );
}
