"use client";

import { useState } from "react";

import { AiConnectForm, type AiConnection } from "@/components/ai/ai-connect-form";
import { AiModelForm } from "@/components/ai/ai-model-form";
import type { AiSettingsOut } from "@/lib/api/ai-types";

/**
 * The language model behind the AI features, in two steps: connect to a provider with a key
 * (its real model list comes back), then pick the model and the reasoning level and save.
 */
export function AiSettingsCard({ settings, canEdit }: { settings: AiSettingsOut; canEdit: boolean }) {
  const savedConnection: AiConnection | null =
    settings.configured && settings.provider
      ? { provider: settings.provider, baseUrl: settings.base_url, apiKey: null, models: null }
      : null;
  const [connection, setConnection] = useState<AiConnection | null>(savedConnection);

  if (!connection) {
    if (!canEdit) return <p className="text-sm text-muted-foreground">No AI model is set up. An admin connects one.</p>;
    return (
      <AiConnectForm
        settings={settings}
        onConnected={setConnection}
        onCancel={savedConnection ? () => setConnection(savedConnection) : undefined}
      />
    );
  }
  return (
    <AiModelForm
      settings={settings}
      connection={connection}
      canEdit={canEdit}
      onChangeConnection={() => setConnection(null)}
    />
  );
}
