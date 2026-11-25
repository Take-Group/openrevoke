"use client";

import { ArrowUpCircleIcon } from "lucide-react";

import { CopyButton } from "@/components/common/copy-button";
import { TextLink } from "@/components/common/links";
import { Notice } from "@/components/common/notice";
import { useSystemVersion } from "@/hooks/use-system";

const UPDATE_COMMAND = "open-revoke update";

/**
 * Admins only: a newer stable release exists (the worker asks GitHub hourly). The update runs on
 * the server, with a database backup first (skills/backend/releases.md); the panel only says so.
 */
export function UpdateNotice({ className }: { className?: string }) {
  const { data } = useSystemVersion();
  if (!data?.update_available || !data.latest_version) return null;
  const security = data.security_update;
  return (
    <Notice
      tone={security ? "warning" : "info"}
      icon={security ? undefined : ArrowUpCircleIcon}
      className={className}
      title={
        security
          ? `Open Revoke ${data.latest_version} fixes a security issue`
          : `Open Revoke ${data.latest_version} is available`
      }
      action={<CopyButton value={UPDATE_COMMAND} label="Copy the update command" />}
    >
      You run {data.version}. On the server, run <code className="font-mono text-xs">{UPDATE_COMMAND}</code>: it backs up
      the database first and goes back if the new version does not start.
      {data.latest_url && (
        <>
          {" "}
          <TextLink href={data.latest_url} external>
            What changed
          </TextLink>
        </>
      )}
    </Notice>
  );
}
