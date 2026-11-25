"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { PageHeader, SETTINGS_COLUMN } from "@/components/common/page-header";
import { QueryState } from "@/components/common/query-state";
import { SettingsSection } from "@/components/settings/settings-section";
import { SlackSetupCard, SlackStatus } from "@/components/slack/slack-setup-card";
import { useAuthState } from "@/hooks/use-auth";
import { useSlackAgent } from "@/hooks/use-slack-agent";

const PAGE = "/settings/slack";

/** Slack's OAuth comes back with ?installed=1 or ?error=…; show it once and clean the URL. */
function useOAuthResult(installed?: string, error?: string) {
  const router = useRouter();
  useEffect(() => {
    if (!installed && !error) return;
    if (installed) toast.success("Installed in Slack");
    if (error) toast.error(error);
    router.replace(PAGE);
  }, [installed, error, router]);
}

/** Settings → Slack: the Slack bot that takes access requests in direct messages. */
export function SlackView({ installed, error }: { installed?: string; error?: string }) {
  useOAuthResult(installed, error);
  const isAdmin = useAuthState().data?.user?.role === "admin";
  const slack = useSlackAgent();
  return (
    <>
      <PageHeader title="Slack" actions={slack.data && <SlackStatus agent={slack.data} canEdit={isAdmin} />} />
      <div className={SETTINGS_COLUMN}>
        <SettingsSection
          title="Slack bot"
          description="People ask for access in a direct message to the bot. Admins approve requests in Slack with one click."
        >
          <QueryState query={slack} feature="Slack bot" rows={3}>
            {(data) => <SlackSetupCard agent={data} canEdit={isAdmin} />}
          </QueryState>
        </SettingsSection>
      </div>
    </>
  );
}
