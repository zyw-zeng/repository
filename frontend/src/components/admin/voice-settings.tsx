"use client";

/** 管理星云、比特和沫沫的 CosyVoice 音色与自动朗读策略。 */

import { LoaderCircle, Play, RotateCcw, Save, Volume2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { SpiritAvatar } from "@/components/spirit/spirit-avatar";
import type { SpiritCharacterId } from "@/components/spirit/types";
import { Button } from "@/components/ui/button";
import { getApiErrorMessage, isUnauthorized } from "@/features/admin/api-error";
import type {
  TtsVoiceProfile,
  TtsVoiceProfileList,
} from "@/features/admin/types";
import { apiClient } from "@/lib/api-client";

interface VoiceSettingsProps {
  onUnauthorized: () => void;
}

export function VoiceSettings({ onUnauthorized }: VoiceSettingsProps) {
  const [profiles, setProfiles] = useState<TtsVoiceProfile[]>([]);
  const [savedProfiles, setSavedProfiles] = useState<TtsVoiceProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<SpiritCharacterId>();
  const [previewingId, setPreviewingId] = useState<SpiritCharacterId>();

  const loadProfiles = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.get<TtsVoiceProfileList>(
        "/tts/profiles",
      );
      setProfiles(response.data.items);
      setSavedProfiles(response.data.items);
    } catch (error) {
      if (isUnauthorized(error)) onUnauthorized();
      else toast.error(getApiErrorMessage(error, "角色音色读取失败。"));
    } finally {
      setLoading(false);
    }
  }, [onUnauthorized]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadProfiles(), 0);
    return () => window.clearTimeout(timer);
  }, [loadProfiles]);

  function updateLocal(
    characterId: SpiritCharacterId,
    changes: Partial<TtsVoiceProfile>,
  ) {
    setProfiles((current) =>
      current.map((item) =>
        item.character_id === characterId ? { ...item, ...changes } : item,
      ),
    );
  }

  async function save(profile: TtsVoiceProfile) {
    setSavingId(profile.character_id);
    try {
      const response = await apiClient.put<TtsVoiceProfile>(
        `/tts/profiles/${profile.character_id}`,
        {
          model: profile.model,
          voice: profile.voice,
          enabled: profile.enabled,
          auto_speak: profile.auto_speak,
        },
      );
      updateLocal(profile.character_id, response.data);
      setSavedProfiles((current) =>
        current.map((item) =>
          item.character_id === profile.character_id ? response.data : item,
        ),
      );
      toast.success(`${profile.display_name}的音色已经生效。`);
      return true;
    } catch (error) {
      if (isUnauthorized(error)) onUnauthorized();
      else toast.error(getApiErrorMessage(error, "角色音色保存失败。"));
      return false;
    } finally {
      setSavingId(undefined);
    }
  }

  function reset(profile: TtsVoiceProfile) {
    /** 放弃当前角色尚未保存的本地修改。 */
    const saved = savedProfiles.find(
      (item) => item.character_id === profile.character_id,
    );
    if (saved) updateLocal(profile.character_id, saved);
  }

  async function preview(profile: TtsVoiceProfile) {
    /** 先保存当前设置，再调用真实 CosyVoice 合成一段短试听。 */
    setPreviewingId(profile.character_id);
    try {
      if (!(await save(profile))) return;
      const response = await apiClient.post<Blob>(
        "/tts/stream",
        {
          text: `你好，我是${profile.display_name}，很高兴和你见面。`,
          character_id: profile.character_id,
          speech_rate: 1,
        },
        {
          responseType: "blob",
          headers: { "X-Request-ID": crypto.randomUUID() },
        },
      );
      const url = URL.createObjectURL(response.data);
      const audio = new Audio(url);
      audio.addEventListener("ended", () => URL.revokeObjectURL(url), {
        once: true,
      });
      await audio.play();
    } catch (error) {
      if (isUnauthorized(error)) onUnauthorized();
      else toast.error(getApiErrorMessage(error, "音色试听失败。"));
    } finally {
      setPreviewingId(undefined);
    }
  }

  return (
    <section className="admin-panel rounded-3xl p-4 sm:p-6">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="flex items-center gap-2 font-semibold">
            <Volume2 className="text-primary size-4" /> 角色声音
          </h2>
          <p className="text-muted-foreground mt-1 text-sm">
            自动朗读会在回答生成到完整句子时立即开始，不等待整段回答完成。
          </p>
        </div>
      </div>

      {loading ? (
        <div className="text-muted-foreground flex items-center justify-center gap-2 py-12 text-sm">
          <LoaderCircle className="size-4 animate-spin" /> 正在读取音色…
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          {profiles.map((profile) => (
            <article
              key={profile.character_id}
              className="admin-card rounded-2xl p-4"
            >
              <div className="mb-4 flex items-center gap-3">
                <div className="bg-muted/50 size-16 rounded-2xl p-1">
                  <SpiritAvatar
                    appearance={{
                      characterId: profile.character_id,
                      outfitId: "classic",
                      accessoryId: "none",
                    }}
                    status="speaking"
                    decorative
                  />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium">{profile.display_name}</h3>
                    {JSON.stringify(profile) !==
                      JSON.stringify(
                        savedProfiles.find(
                          (item) => item.character_id === profile.character_id,
                        ),
                      ) && (
                      <span className="bg-amber-500/10 text-amber-700 dark:text-amber-300 rounded-full px-2 py-0.5 text-[10px]">
                        未保存
                      </span>
                    )}
                  </div>
                  <p className="text-muted-foreground text-xs">
                    {profile.character_id}
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                <label className="block">
                  <span className="text-muted-foreground mb-1.5 block text-xs">
                    CosyVoice 模型
                  </span>
                  <input
                    value={profile.model}
                    onChange={(event) =>
                      updateLocal(profile.character_id, {
                        model: event.target.value,
                      })
                    }
                    className="bg-background/70 focus:border-primary/50 h-10 w-full rounded-xl border px-3 text-sm outline-none"
                  />
                </label>
                <label className="block">
                  <span className="text-muted-foreground mb-1.5 block text-xs">
                    音色 ID
                  </span>
                  <input
                    value={profile.voice}
                    onChange={(event) =>
                      updateLocal(profile.character_id, {
                        voice: event.target.value,
                      })
                    }
                    placeholder="例如 longanyang"
                    className="bg-background/70 focus:border-primary/50 h-10 w-full rounded-xl border px-3 text-sm outline-none"
                  />
                </label>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <label className="bg-muted/35 flex items-center gap-2 rounded-xl px-3 py-2.5">
                    <input
                      type="checkbox"
                      checked={profile.enabled}
                      onChange={(event) =>
                        updateLocal(profile.character_id, {
                          enabled: event.target.checked,
                        })
                      }
                      className="accent-primary size-4"
                    />
                    启用语音
                  </label>
                  <label className="bg-muted/35 flex items-center gap-2 rounded-xl px-3 py-2.5">
                    <input
                      type="checkbox"
                      checked={profile.auto_speak}
                      disabled={!profile.enabled}
                      onChange={(event) =>
                        updateLocal(profile.character_id, {
                          auto_speak: event.target.checked,
                        })
                      }
                      className="accent-primary size-4"
                    />
                    自动朗读
                  </label>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    variant="outline"
                    onClick={() => void preview(profile)}
                    disabled={
                      previewingId === profile.character_id ||
                      !profile.enabled ||
                      !profile.model.trim() ||
                      !profile.voice.trim()
                    }
                  >
                    {previewingId === profile.character_id ? (
                      <LoaderCircle className="animate-spin" />
                    ) : (
                      <Play />
                    )}
                    {previewingId === profile.character_id ? "试听中" : "保存并试听"}
                  </Button>
                  <Button
                    onClick={() => void save(profile)}
                    disabled={
                      savingId === profile.character_id ||
                      !profile.model.trim() ||
                      !profile.voice.trim()
                    }
                  >
                    {savingId === profile.character_id ? (
                      <LoaderCircle className="animate-spin" />
                    ) : (
                      <Save />
                    )}
                    {savingId === profile.character_id ? "保存中" : "保存"}
                  </Button>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full"
                  onClick={() => reset(profile)}
                >
                  <RotateCcw /> 放弃未保存修改
                </Button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
