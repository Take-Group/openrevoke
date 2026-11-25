"use client";

import { PlugIcon } from "lucide-react";
import { useState } from "react";

import { FormField } from "@/components/common/form-field";
import { InlineError } from "@/components/common/notice";
import { OptionSelect } from "@/components/common/option-select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAiModels } from "@/hooks/use-ai-settings";
import { errorMessage } from "@/lib/api/client";
import { emptyToNull } from "@/lib/format";
import type { AiModelOut, AiProvider, AiSettingsOut } from "@/lib/api/ai-types";

/** A provider the admin connected to: its models came back, so the key and URL work. */
export interface AiConnection {
  provider: AiProvider;
  baseUrl: string | null;
  /** Null: the saved key of the same provider. */
  apiKey: string | null;
  /** Null: not loaded yet (the saved connection loads them itself). */
  models: AiModelOut[] | null;
}

/** Step 1: provider, base URL and key. "Connect" asks the provider for its models. */
export function AiConnectForm({
  settings,
  onConnected,
  onCancel,
}: {
  settings: AiSettingsOut;
  onConnected: (connection: AiConnection) => void;
  onCancel?: () => void;
}) {
  const [provider, setProvider] = useState<AiProvider>(settings.provider ?? "anthropic");
  const [baseUrl, setBaseUrl] = useState(settings.base_url ?? "");
  const [apiKey, setApiKey] = useState("");
  const connect = useAiModels();
  const info = settings.providers.find((item) => item.provider === provider) ?? settings.providers[0];
  const keySaved = settings.api_key_set && settings.provider === provider;
  const showBaseUrl = provider === "custom" || provider === "openrouter";
  const ready = (!info.needs_api_key || keySaved || apiKey.trim() !== "") && (!info.needs_base_url || baseUrl.trim() !== "");

  const pickProvider = (value: AiProvider) => {
    setProvider(value);
    setBaseUrl(value === settings.provider ? (settings.base_url ?? "") : "");
    setApiKey("");
    connect.reset();
  };

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        const key = apiKey.trim() || null;
        const url = showBaseUrl ? emptyToNull(baseUrl) : null;
        connect.mutate(
          { provider, base_url: url, api_key: key },
          { onSuccess: (data) => onConnected({ provider, baseUrl: url, apiKey: key, models: data.models }) },
        );
      }}
    >
      <FormField label="Provider" htmlFor="ai-provider">
        <OptionSelect
          id="ai-provider"
          value={provider}
          onChange={(next) => next && pickProvider(next as AiProvider)}
          options={settings.providers.map((item) => ({ value: item.provider, label: item.label }))}
        />
      </FormField>
      {showBaseUrl && (
        <FormField
          label="Base URL"
          htmlFor="ai-base-url"
          required={info.needs_base_url}
          hint={provider === "custom" ? "OpenAI-compatible API, e.g. https://llm.example.com/v1" : undefined}
        >
          <Input
            id="ai-base-url"
            type="url"
            required={info.needs_base_url}
            placeholder={info.default_base_url ?? "https://"}
            value={baseUrl}
            onChange={(event) => setBaseUrl(event.target.value)}
          />
        </FormField>
      )}
      <FormField label="API key" htmlFor="ai-key" required={info.needs_api_key && !keySaved}>
        <Input
          id="ai-key"
          type="password"
          autoComplete="off"
          placeholder={keySaved ? "Saved. Type to replace" : info.needs_api_key ? "" : "Optional"}
          value={apiKey}
          onChange={(event) => setApiKey(event.target.value)}
        />
      </FormField>
      {connect.isError && <InlineError message={errorMessage(connect.error)} />}
      <div className="flex items-center gap-2">
        <Button type="submit" disabled={!ready || connect.isPending}>
          <PlugIcon />
          {connect.isPending ? "Connecting…" : "Connect"}
        </Button>
        {onCancel && (
          <Button type="button" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}
