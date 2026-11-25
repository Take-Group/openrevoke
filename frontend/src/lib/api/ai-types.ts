/** Types of the AI model settings (/api/ai-settings), from docs/openapi.json. */

import type { DateTimeString } from "@/lib/api/types";

export type AiProvider = "anthropic" | "openai" | "openrouter" | "custom";
export type AiReasoningEffort = "low" | "medium" | "high" | "xhigh" | "max";

export interface AiProviderOut {
  provider: AiProvider;
  label: string;
  default_base_url: string | null;
  default_model: string | null;
  /** The base URL is required (custom endpoint). */
  needs_base_url: boolean;
  needs_api_key: boolean;
}

export interface AiSettingsOut {
  /** A model is saved; the agents can answer. */
  configured: boolean;
  provider: AiProvider | null;
  model: string | null;
  base_url: string | null;
  /** Null: the provider's default for the model. */
  reasoning_effort: AiReasoningEffort | null;
  api_key_set: boolean;
  updated_at: DateTimeString | null;
  providers: AiProviderOut[];
}

export interface AiSettingsUpdate {
  provider: AiProvider;
  model: string;
  base_url?: string | null;
  /** Null keeps the saved key (same provider only). */
  api_key?: string | null;
  reasoning_effort?: AiReasoningEffort | null;
}

export interface AiModelsRequest {
  provider: AiProvider;
  base_url?: string | null;
  api_key?: string | null;
}

export interface AiModelOut {
  id: string;
  /** Display name; the id when the provider sends none. */
  name: string;
  /** Reasoning levels the model takes; empty: none; null: the provider does not say. */
  efforts: AiReasoningEffort[] | null;
}

export interface AiModelList {
  models: AiModelOut[];
}

export interface AiTestResult {
  ok: boolean;
  reply: string | null;
  error: string | null;
}
