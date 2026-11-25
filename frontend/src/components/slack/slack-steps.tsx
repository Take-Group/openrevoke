"use client";

import { ImageUpIcon, RotateCcwIcon } from "lucide-react";
import { useState } from "react";

import { FileButton } from "@/components/common/file-button";
import { FormField } from "@/components/common/form-field";
import { TextLink } from "@/components/common/links";
import { Notice } from "@/components/common/notice";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useCreateSlackApp, useSaveSlackTokens, useSetSlackAvatar } from "@/hooks/use-slack-agent";
import type { SlackAgentOut } from "@/lib/api/slack-types";

const CONFIG_TOKENS_URL = "https://api.slack.com/apps";

/** Step 1 without an app: a configuration token creates it from the manifest. */
export function CreateAppForm({ agent }: { agent: SlackAgentOut }) {
  const [botName, setBotName] = useState(agent.bot_name ?? "Open Revoke");
  const [token, setToken] = useState("");
  const [refresh, setRefresh] = useState("");
  const create = useCreateSlackApp();
  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        create.mutate({ bot_name: botName.trim(), config_token: token.trim(), config_refresh_token: refresh.trim() || null });
      }}
    >
      <p className="text-[0.8125rem] text-muted-foreground">
        At the bottom of{" "}
        <TextLink href={CONFIG_TOKENS_URL} external>
          api.slack.com/apps
        </TextLink>{" "}
        click <b>Generate Token</b> under “Your App Configuration Tokens”, pick the workspace and paste both tokens.
      </p>
      <FormField label="Bot name" htmlFor="slack-bot-name" required>
        <Input id="slack-bot-name" required maxLength={35} value={botName} onChange={(event) => setBotName(event.target.value)} />
      </FormField>
      <FormField label="Access token" htmlFor="slack-config-token" required hint="Starts with xoxe.xoxp-. Valid 12 hours.">
        <Input id="slack-config-token" type="password" autoComplete="off" required value={token} onChange={(event) => setToken(event.target.value)} />
      </FormField>
      <FormField label="Refresh token" htmlFor="slack-config-refresh" hint="Starts with xoxe-. Lets Open Revoke change the icon later.">
        <Input id="slack-config-refresh" type="password" autoComplete="off" value={refresh} onChange={(event) => setRefresh(event.target.value)} />
      </FormField>
      <div className="flex flex-wrap items-center gap-2">
        <Button type="submit" size="sm" disabled={!token.trim() || !botName.trim() || create.isPending}>
          {create.isPending ? "Creating…" : "Create app"}
        </Button>
        <TextLink href={agent.manifest_url} external className="text-[0.8125rem] font-normal text-muted-foreground">
          or create it by hand from the manifest
        </TextLink>
      </div>
    </form>
  );
}

/** The app icon: set by Open Revoke right after creation; a new one needs the configuration token. */
export function AvatarRow({ agent }: { agent: SlackAgentOut }) {
  const setAvatar = useSetSlackAvatar();
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-muted-foreground">Icon:</span>
        {agent.avatar_set_at ? <span>set</span> : <span className="text-muted-foreground">Slack default</span>}
        {agent.has_config_token && (
          <>
            <FileButton
              accept="image/png,image/jpeg"
              variant="outline"
              size="xs"
              disabled={setAvatar.isPending}
              onFile={(file) => setAvatar.mutate(file)}
            >
              <ImageUpIcon />
              Upload
            </FileButton>
            <Button type="button" variant="ghost" size="xs" disabled={setAvatar.isPending} onClick={() => setAvatar.mutate(null)}>
              <RotateCcwIcon />
              Default
            </Button>
          </>
        )}
      </div>
      {agent.avatar_error && <Notice tone="warning">Icon not set: {agent.avatar_error}</Notice>}
    </div>
  );
}

/** Paste one token (bot or app-level); the API checks it with Slack before saving. */
export function TokenForm({ kind, placeholder }: { kind: "bot_token" | "app_token"; placeholder: string }) {
  const [value, setValue] = useState("");
  const save = useSaveSlackTokens();
  return (
    <form
      className="flex gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        save.mutate({ [kind]: value.trim() }, { onSuccess: () => setValue("") });
      }}
    >
      <Input
        aria-label={kind === "bot_token" ? "Bot token" : "App-level token"}
        type="password"
        autoComplete="off"
        placeholder={placeholder}
        value={value}
        onChange={(event) => setValue(event.target.value)}
      />
      <Button type="submit" disabled={!value.trim() || save.isPending}>
        Save
      </Button>
    </form>
  );
}
