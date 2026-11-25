"use client";

import { CheckCircle2Icon, PlugZapIcon } from "lucide-react";
import { useState } from "react";

import type { AiConnection } from "@/components/ai/ai-connect-form";
import { FormField } from "@/components/common/form-field";
import { InlineError } from "@/components/common/notice";
import { OptionSelect } from "@/components/common/option-select";
import { SearchableSelect } from "@/components/common/searchable-select";
import { Spinner } from "@/components/common/spinner";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { useSaveAiSettings, useSavedAiModels, useTestAi } from "@/hooks/use-ai-settings";
import { errorMessage } from "@/lib/api/client";
import type { AiModelOut, AiReasoningEffort, AiSettingsOut } from "@/lib/api/ai-types";

const EFFORT_LABEL: Record<AiReasoningEffort, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  xhigh: "Extra high",
  max: "Max",
};
/** Offered when the provider does not say which levels a model takes (OpenAI, custom endpoints). */
const COMMON_EFFORTS: AiReasoningEffort[] = ["low", "medium", "high"];
const DEFAULT = "default";

/** Step 2: the connected provider, its models and the reasoning level; Save, then Test. */
export function AiModelForm({
  settings,
  connection,
  canEdit,
  onChangeConnection,
}: {
  settings: AiSettingsOut;
  connection: AiConnection;
  canEdit: boolean;
  onChangeConnection: () => void;
}) {
  const saved = useSavedAiModels(connection.provider, connection.baseUrl, connection.models === null);
  const models = connection.models ?? saved.data?.models ?? null;
  const isSavedConnection =
    connection.apiKey === null && connection.provider === settings.provider && connection.baseUrl === settings.base_url;
  const info = settings.providers.find((item) => item.provider === connection.provider);

  const [pickedModel, setPickedModel] = useState<string | null>(null);
  const [pickedEffort, setPickedEffort] = useState<AiReasoningEffort | null | undefined>(undefined);
  const fallbackModel = isSavedConnection ? settings.model : models?.some((m) => m.id === info?.default_model) ? info?.default_model : null;
  const model = pickedModel ?? fallbackModel ?? "";
  const current = models?.find((item) => item.id === model);
  const efforts = current ? (current.efforts ?? COMMON_EFFORTS) : [];
  const wanted = pickedEffort === undefined ? (isSavedConnection ? settings.reasoning_effort : null) : pickedEffort;
  const effort = wanted && efforts.includes(wanted) ? wanted : null;

  const save = useSaveAiSettings();
  const test = useTestAi();
  const changed = !isSavedConnection || model !== settings.model || effort !== settings.reasoning_effort;

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        save.mutate({
          provider: connection.provider,
          model,
          base_url: connection.baseUrl,
          api_key: connection.apiKey,
          reasoning_effort: effort,
        });
      }}
    >
      <div className="flex items-start justify-between gap-3 rounded-lg border border-frame px-3 py-2.5">
        <div className="flex min-w-0 flex-col gap-1 text-sm">
          <div className="flex items-center gap-2">
            <span className="font-medium">{info?.label ?? connection.provider}</span>
            <StatusBadge
              status={models ? "connected" : saved.isError ? "error" : "connecting"}
              label={models ? "Connected" : saved.isError ? "Not connected" : "Connecting"}
            />
          </div>
          <span className="truncate text-xs text-muted-foreground">
            {[connection.baseUrl, models ? `${models.length} models` : null].filter(Boolean).join(" · ")}
          </span>
        </div>
        {canEdit && (
          <Button type="button" variant="outline" size="sm" onClick={onChangeConnection}>
            Change
          </Button>
        )}
      </div>

      {models === null ? (
        saved.isError ? (
          <InlineError message={`Cannot load the models: ${errorMessage(saved.error)}`} />
        ) : (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner /> Loading the models…
          </p>
        )
      ) : (
        <>
          <FormField label="Model" htmlFor="ai-model" required>
            <SearchableSelect
              id="ai-model"
              disabled={!canEdit}
              value={model}
              onChange={setPickedModel}
              placeholder="Choose a model"
              searchPlaceholder="Search models"
              groups={[{ options: models.map(modelOption) }]}
            />
          </FormField>
          <FormField label="Reasoning" htmlFor="ai-effort" hint={effortHint(current)}>
            <OptionSelect
              id="ai-effort"
              disabled={!canEdit || !current || efforts.length === 0}
              value={effort ?? DEFAULT}
              onChange={(next) => setPickedEffort(!next || next === DEFAULT ? null : (next as AiReasoningEffort))}
              options={[
                { value: DEFAULT, label: "Model default" },
                ...efforts.map((level) => ({ value: level, label: EFFORT_LABEL[level] })),
              ]}
            />
          </FormField>
        </>
      )}

      {canEdit && (
        <div className="flex flex-wrap items-center gap-2">
          <Button type="submit" disabled={!changed || !current || save.isPending}>
            Save
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={!settings.configured || changed || test.isPending}
            onClick={() => test.mutate()}
          >
            <PlugZapIcon />
            {test.isPending ? "Testing…" : "Test"}
          </Button>
          {test.data?.ok && (
            <span className="flex items-center gap-1 text-sm text-success">
              <CheckCircle2Icon className="size-4" />
              Works: “{test.data.reply}”
            </span>
          )}
        </div>
      )}
      {test.data && !test.data.ok && <InlineError message={test.data.error} />}
    </form>
  );
}

function modelOption(model: AiModelOut) {
  return { value: model.id, label: model.name, hint: model.name === model.id ? undefined : model.id, keywords: [model.id] };
}

function effortHint(model: AiModelOut | undefined): string | undefined {
  if (!model) return undefined;
  if (model.efforts === null) return "The provider does not say which models reason. Test checks that this one takes the level.";
  if (model.efforts.length === 0) return "This model has no reasoning setting.";
  return "Higher levels think longer: better answers on hard requests, more tokens.";
}
