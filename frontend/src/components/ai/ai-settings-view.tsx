"use client";

import { AiSettingsCard } from "@/components/ai/ai-settings-card";
import { PageHeader, SETTINGS_COLUMN } from "@/components/common/page-header";
import { QueryState } from "@/components/common/query-state";
import { SettingsSection } from "@/components/settings/settings-section";
import { useAiSettings } from "@/hooks/use-ai-settings";
import { useAuthState } from "@/hooks/use-auth";

/** Settings → AI model: one language model for every AI feature of the panel. */
export function AiSettingsView() {
  const isAdmin = useAuthState().data?.user?.role === "admin";
  const ai = useAiSettings();
  return (
    <>
      <PageHeader title="AI model" />
      <div className={SETTINGS_COLUMN}>
        <SettingsSection
          title="AI model"
          description="The language model Open Revoke uses wherever it needs AI, such as the Slack bot. Your key, your provider."
        >
          <QueryState query={ai} feature="AI settings" rows={3}>
            {(data) => (
              <div className="max-w-md">
                <AiSettingsCard
                  key={`${data.provider}-${data.model}-${data.base_url}-${data.reasoning_effort}-${data.api_key_set}`}
                  settings={data}
                  canEdit={isAdmin}
                />
              </div>
            )}
          </QueryState>
        </SettingsSection>
      </div>
    </>
  );
}
