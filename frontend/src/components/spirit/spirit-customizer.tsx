"use client";

/** 提供角色、服装和配饰选择，并即时预览组合后的 SVG 精灵。 */

import { RotateCcw, Shirt, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

import {
  DEFAULT_SPIRIT_APPEARANCE,
  spiritAccessories,
  spiritCharacters,
  spiritOutfits,
} from "./appearances";
import { SpiritAvatar } from "./spirit-avatar";
import type { SpiritAppearance } from "./types";

interface SpiritCustomizerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  appearance: SpiritAppearance;
  onAppearanceChange: (appearance: SpiritAppearance) => void;
  mobile?: boolean;
}

export function SpiritCustomizer({
  open,
  onOpenChange,
  appearance,
  onAppearanceChange,
  mobile = false,
}: SpiritCustomizerProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side={mobile ? "bottom" : "right"}
        className={cn(
          "overflow-y-auto",
          mobile &&
            "max-h-[82dvh] rounded-t-3xl pb-[env(safe-area-inset-bottom)]",
        )}
      >
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Shirt className="size-4" /> 精灵换装间
          </SheetTitle>
          <SheetDescription>
            形象只保存在当前浏览器，不会上传个人偏好。
          </SheetDescription>
        </SheetHeader>
        <div className="mx-auto w-36">
          <SpiritAvatar appearance={appearance} status="idle" decorative />
        </div>
        <div className="space-y-6 px-4 pb-6">
          <section>
            <h3 className="mb-2 text-xs font-semibold tracking-wider uppercase">
              选择形象
            </h3>
            <div className="grid grid-cols-3 gap-2">
              {spiritCharacters.map((character) => (
                <button
                  key={character.id}
                  type="button"
                  aria-pressed={appearance.characterId === character.id}
                  onClick={() =>
                    onAppearanceChange({
                      ...appearance,
                      characterId: character.id,
                    })
                  }
                  className={cn(
                    "rounded-2xl border p-2 text-left transition-colors",
                    appearance.characterId === character.id
                      ? "border-primary bg-primary/10"
                      : "hover:bg-muted",
                  )}
                >
                  <span className="mx-auto mb-2 block size-16">
                    <SpiritAvatar
                      appearance={{
                        characterId: character.id,
                        outfitId: "classic",
                        accessoryId: "none",
                      }}
                      status="idle"
                      decorative
                    />
                  </span>
                  <span className="block text-xs font-medium">
                    {character.name}
                  </span>
                </button>
              ))}
            </div>
          </section>
          <section>
            <h3 className="mb-2 text-xs font-semibold tracking-wider uppercase">
              选择服装
            </h3>
            <div className="grid gap-2">
              {spiritOutfits.map((outfit) => (
                <button
                  key={outfit.id}
                  type="button"
                  aria-pressed={appearance.outfitId === outfit.id}
                  onClick={() =>
                    onAppearanceChange({ ...appearance, outfitId: outfit.id })
                  }
                  className={cn(
                    "rounded-xl border px-3 py-2 text-left transition-colors",
                    appearance.outfitId === outfit.id
                      ? "border-primary bg-primary/10"
                      : "hover:bg-muted",
                  )}
                >
                  <span className="block text-sm font-medium">
                    {outfit.name}
                  </span>
                  <span className="text-muted-foreground text-xs">
                    {outfit.description}
                  </span>
                </button>
              ))}
            </div>
          </section>
          <fieldset>
            <legend className="mb-2 text-xs font-semibold tracking-wider uppercase">
              选择配饰
            </legend>
            <div className="flex flex-wrap gap-2">
              {spiritAccessories.map((accessory) => (
                <Button
                  key={accessory.id}
                  type="button"
                  variant={
                    appearance.accessoryId === accessory.id
                      ? "default"
                      : "outline"
                  }
                  size="sm"
                  onClick={() =>
                    onAppearanceChange({
                      ...appearance,
                      accessoryId: accessory.id,
                    })
                  }
                >
                  <Sparkles data-icon="inline-start" />
                  {accessory.name}
                </Button>
              ))}
            </div>
          </fieldset>
          <Button
            type="button"
            variant="ghost"
            className="w-full"
            onClick={() => onAppearanceChange(DEFAULT_SPIRIT_APPEARANCE)}
          >
            <RotateCcw data-icon="inline-start" />
            恢复默认装扮
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
