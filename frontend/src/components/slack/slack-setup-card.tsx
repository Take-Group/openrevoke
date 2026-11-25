"use client";

import { Trash2Icon } from "lucide-react";
import { useState } from "react";

import { AvatarRow, CreateAppForm, TokenForm } from "@/components/slack/slack-steps";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { ExternalLinkButton, LinkButton } from "@/components/common/links";
import { InlineError, Notice } from "@/components/common/notice";
import { StatusBadge } from "@/components/common/status-badge";
import { Step, Steps, type StepState } from "@/components/common/steps";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useRemoveSlackAgent, useUpdateSlackAgent } from "@/hooks/use-slack-agent";
import type { SlackAgentOut } from "@/lib/api/slack-types";

/** Status line: connection badge and the on/off switch once both tokens are saved. */
export function SlackStatus({ agent, canEdit }: { agent: SlackAgentOut; canEdit: boolean }) {
  const update = useUpdateSlackAgent();
  const ready = agent.has_bot_token && agent.has_app_token;
  return (
    <div className="flex items-center gap-3">
      <StatusBadge status={agent.status} />
      {ready && (
        <div className="flex items-center gap-2">
          <Switch
            id="slack-agent-enabled"
            checked={agent.enabled}
            disabled={!canEdit || update.isPending}
            onCheckedChange={(checked) => update.mutate(checked)}
          />
          <Label htmlFor="slack-agent-enabled" className="font-normal">
            On
          </Label>
        </div>
      )}
    </div>
  );
}

/** Done steps show a check, the first open one is active, the rest wait. */
function stepStates(done: boolean[]): StepState[] {
  const firstOpen = done.indexOf(false);
  return done.map((isDone, index) => (isDone ? "done" : index === firstOpen ? "active" : "todo"));
}

/** Three steps: create the app (with its icon), install it, give it a Socket Mode token. */
export function SlackSetupCard({ agent, canEdit }: { agent: SlackAgentOut; canEdit: boolean }) {
  const [removing, setRemoving] = useState(false);
  const remove = useRemoveSlackAgent();
  const hasApp = Boolean(agent.app_id);
  const ready = agent.has_bot_token && agent.has_app_token;
  const [createState, installState, socketState] = stepStates([hasApp || agent.has_bot_token, agent.has_bot_token, agent.has_app_token]);
  return (
    <div className="flex flex-col gap-5">
      {!agent.ai_configured && (
        <Notice
          tone="warning"
          action={
            <LinkButton href="/settings/ai" variant="outline" size="sm">
              Set up AI model
            </LinkButton>
          }
        >
          Choose the AI model first: the bot answers with it.
        </Notice>
      )}
      <Steps>
        <Step
          n={1}
          title="Create the Slack app"
          state={createState}
          description={
            !hasApp && agent.has_bot_token ? (
              "Created by hand. Set its icon in the Slack app settings, Display Information."
            ) : hasApp ? (
              <>
                <b className="font-medium text-foreground">{agent.bot_name}</b> · app {agent.app_id}
              </>
            ) : undefined
          }
        >
          {hasApp ? <AvatarRow agent={agent} /> : !agent.has_bot_token && canEdit ? <CreateAppForm agent={agent} /> : null}
        </Step>
        <Step
          n={2}
          title="Install it in the workspace"
          state={installState}
          description={
            agent.has_bot_token ? (
              `Installed in ${agent.team_name ?? "the workspace"}.`
            ) : canEdit && !agent.oauth_install ? (
              <>
                After “Allow”, copy the <b className="font-medium text-foreground">Bot User OAuth Token</b> from OAuth
                &amp; Permissions.
              </>
            ) : undefined
          }
        >
          {!agent.has_bot_token && canEdit && (
            <>
              {agent.install_url && (
                <ExternalLinkButton href={agent.install_url} variant="default">
                  Install to Slack
                </ExternalLinkButton>
              )}
              {!agent.oauth_install && <TokenForm kind="bot_token" placeholder="xoxb-…" />}
            </>
          )}
        </Step>
        <Step
          n={3}
          title="Connect over Socket Mode"
          state={socketState}
          description={
            agent.has_app_token ? (
              "App-level token saved."
            ) : canEdit ? (
              <>
                In Basic Information → App-Level Tokens, click <b className="font-medium text-foreground">Generate Token and Scopes</b>,
                add the scope <code className="font-mono text-xs text-foreground">connections:write</code> and paste the token.
                Slack has no API for this one.
              </>
            ) : undefined
          }
        >
          {!agent.has_app_token && canEdit && (
            <>
              {agent.app_token_url && <ExternalLinkButton href={agent.app_token_url}>Open app settings</ExternalLinkButton>}
              <TokenForm kind="app_token" placeholder="xapp-…" />
            </>
          )}
        </Step>
      </Steps>
      {agent.last_error && <InlineError message={agent.last_error} />}
      {ready && agent.status === "connected" && (
        <Notice tone="info">
          People write to <b>@{agent.bot_name}</b> in Slack, e.g. “I need access to Notion”. Admins on Slack get
          requests that need approval with Approve and Reject buttons.
        </Notice>
      )}
      {canEdit && (hasApp || agent.has_bot_token || agent.has_app_token) && (
        <div className="flex justify-end">
          <Button variant="ghost" size="sm" onClick={() => setRemoving(true)}>
            <Trash2Icon />
            Remove
          </Button>
        </div>
      )}
      <ConfirmDialog
        open={removing}
        onOpenChange={setRemoving}
        icon={Trash2Icon}
        title="Remove the Slack app from Open Revoke?"
        description="Open Revoke forgets the app and its tokens. The app stays in Slack: delete it at api.slack.com/apps."
        confirmLabel="Remove"
        destructive
        pending={remove.isPending}
        onConfirm={() => remove.mutate(undefined, { onSuccess: () => setRemoving(false) })}
      />
    </div>
  );
}
