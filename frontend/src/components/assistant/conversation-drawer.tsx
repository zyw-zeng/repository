"use client";

/** 在不增加新页面的前提下，以抽屉展示当前浏览器保存的会话索引。 */

import { Clock3, History, MessageSquareText, Plus, X } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import type { LocalConversation } from "@/features/chat/types";

interface ConversationDrawerProps {
  conversations: LocalConversation[];
  activeId?: string;
  disabled: boolean;
  onSelect: (conversation: LocalConversation) => void;
  onRemove: (id: string) => void;
  onCreate: () => void;
}

function formatUpdatedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "最近使用";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function ConversationDrawer({
  conversations,
  activeId,
  disabled,
  onSelect,
  onRemove,
  onCreate,
}: ConversationDrawerProps) {
  const [open, setOpen] = useState(false);

  function selectAndClose(conversation: LocalConversation) {
    onSelect(conversation);
    setOpen(false);
  }

  function createAndClose() {
    onCreate();
    setOpen(false);
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger
        render={
          <Button variant="ghost" size="icon" aria-label="打开历史会话" />
        }
      >
        <History />
      </SheetTrigger>
      <SheetContent side="right" className="w-[88vw] sm:max-w-md">
        <SheetHeader className="border-border/60 border-b px-5 py-5">
          <SheetTitle>历史会话</SheetTitle>
          <SheetDescription>仅显示保存在当前浏览器中的会话。</SheetDescription>
        </SheetHeader>
        <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-4">
          <Button
            className="w-full"
            onClick={createAndClose}
            disabled={disabled}
          >
            <Plus data-icon="inline-start" /> 开始新对话
          </Button>
          {conversations.length === 0 ? (
            <div className="text-muted-foreground grid flex-1 place-items-center py-12 text-center text-sm">
              <div>
                <MessageSquareText className="mx-auto mb-3 size-8 opacity-50" />
                <p>还没有本地会话</p>
                <p className="mt-1 text-xs">发送第一个问题后会自动保存索引。</p>
              </div>
            </div>
          ) : (
            <ul className="space-y-2 pb-6">
              {conversations.map((conversation) => (
                <li key={conversation.id}>
                  <div
                    className={`group flex items-center rounded-xl border transition-colors ${
                      conversation.id === activeId
                        ? "border-primary/45 bg-primary/8"
                        : "hover:bg-muted/60"
                    }`}
                  >
                    <button
                      type="button"
                      className="min-w-0 flex-1 px-3 py-3 text-left"
                      onClick={() => selectAndClose(conversation)}
                      disabled={disabled}
                    >
                      <span className="block truncate text-sm font-medium">
                        {conversation.title}
                      </span>
                      <span className="text-muted-foreground mt-1 flex items-center gap-1 text-xs">
                        <Clock3 className="size-3" />{" "}
                        {formatUpdatedAt(conversation.updatedAt)}
                      </span>
                    </button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      className="mr-2 opacity-60 hover:opacity-100"
                      aria-label={`从本机列表移除：${conversation.title}`}
                      onClick={() => onRemove(conversation.id)}
                      disabled={disabled}
                    >
                      <X />
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
