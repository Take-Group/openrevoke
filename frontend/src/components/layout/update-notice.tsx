"use client";

import { ArrowUpCircleIcon } from "lucide-react";

import { CopyButton } from "@/components/common/copy-button";
import { TextLink } from "@/components/common/links";
import { Notice } from "@/components/common/notice";
import { useSystemVersion } from "@/hooks/use-system";

const UPDATE_COMMAND = "open-revoke update";
const HELM_CHART = "oci://ghcr.io/take-group/charts/openrevoke";

/**
 * Admins only: a newer stable release exists (the worker asks GitHub hourly). The update runs on
 * the server, with a database backup first (skills/backend/releases.md); the panel only says so.
 * A Helm install (docs/kubernetes.md) gets the `helm upgrade` command instead: the chart has no
 * automatic backup or rollback.
 */
export function UpdateNotice({ className }: { className?: string }) {
  const { data } = useSystemVersion();
  if (!data?.update_available || !data.latest_version) return null;
  const security = data.security_update;
  const helm = data.install_method === "helm";
  const command = helm ? `helm upgrade <release> ${HELM_CHART} --version ${data.latest_version}` : UPDATE_COMMAND;
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
      action={<CopyButton value={command} label="Copy the update command" />}
    >
      {helm ? (
        <>
          You run {data.version}. Back up the database, then run{" "}
          <code className="font-mono text-xs break-all">{command}</code> with the name of your Helm release.
        </>
      ) : (
        <>
          You run {data.version}. On the server, run <code className="font-mono text-xs">{command}</code>: it backs up the
          database first and goes back if the new version does not start.
        </>
      )}
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
