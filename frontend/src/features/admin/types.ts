/** 复用 OpenAPI 自动生成类型，避免管理端手写重复接口结构。 */

import type { components } from "@/types/api.generated";

export type AdminToken = components["schemas"]["AdminTokenResponse"];
export type DocumentItem = components["schemas"]["DocumentResponse"];
export type DocumentList = components["schemas"]["DocumentListResponse"];
export type DocumentAccepted =
  components["schemas"]["DocumentAcceptedResponse"];
export type IngestionJob = components["schemas"]["JobResponse"];
export type IngestionJobList = components["schemas"]["JobListResponse"];

export type TtsVoiceProfile = components["schemas"]["TtsVoiceProfileResponse"];
export type TtsVoiceProfileList =
  components["schemas"]["TtsVoiceProfileListResponse"];

export type AdminAuthState = "checking" | "anonymous" | "authenticated";
