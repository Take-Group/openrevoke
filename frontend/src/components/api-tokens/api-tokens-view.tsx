"use client";

import { KeyRoundIcon, PlusIcon } from "lucide-react";
import { useState } from "react";

import { McpSetupGuide } from "@/components/api-tokens/mcp-setup-guide";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { CopyField } from "@/components/common/copy-button";
import { EmptyState } from "@/components/common/empty-state";
import { LinkButton } from "@/components/common/links";
import { PageHeader, SETTINGS_COLUMN } from "@/components/common/page-header";
import { Panel } from "@/components/common/panel";
import { QueryState } from "@/components/common/query-state";
import { RelativeTime } from "@/components/common/relative-time";
import { TagBadge } from "@/components/common/status-badge";
import { SettingsSection } from "@/components/settings/settings-section";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useApiTokens, useRevokeApiToken } from "@/hooks/use-api-tokens";
import type { ApiTokenOut } from "@/lib/api/api-token-types";
import { SCOPE_LABEL } from "@/components/api-tokens/scope";



function TokensTable({ tokens, onRevoke }: { tokens: ApiTokenOut[]; onRevoke: (token: ApiTokenOut) => void }) {
  if (tokens.length === 0) {
    return (
      <Panel>
        <EmptyState
          icon={KeyRoundIcon}
          title="No tokens yet"
          description="Create one to connect an AI assistant or a script."
          className="py-8"
        />
      </Panel>
    );
  }
  return (
    <Panel>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Access</TableHead>
            <TableHead className="max-md:hidden">Token</TableHead>
            <TableHead className="max-md:hidden">Last used</TableHead>
            <TableHead className="w-px" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {tokens.map((token) => (
            <TableRow key={token.id}>
              <TableCell>
                <div className="font-medium">{token.name}</div>
                <div className="text-xs text-muted-foreground">
                  Created <RelativeTime value={token.created_at} />
                </div>
              </TableCell>
              <TableCell>
                <TagBadge>{SCOPE_LABEL[token.scope]}</TagBadge>
              </TableCell>
              <TableCell className="font-mono text-xs text-muted-foreground max-md:hidden">{token.prefix}…</TableCell>
              <TableCell className="max-md:hidden">
                {token.last_used_at ? <RelativeTime value={token.last_used_at} /> : <span className="text-muted-foreground">Never</span>}
              </TableCell>
              <TableCell className="text-right">
                <Button variant="ghost" size="sm" onClick={() => onRevoke(token)}>
                  Revoke
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Panel>
  );
}

/** `/settings/api`: the MCP server address with setup snippets, and the user's API tokens. */
export function ApiTokensView() {
  const tokens = useApiTokens();
  const revoke = useRevokeApiToken();
  const [revoking, setRevoking] = useState<ApiTokenOut | null>(null);
  return (
    <>
      <PageHeader title="API and MCP" />
      <div className={SETTINGS_COLUMN}>
        <QueryState query={tokens} feature="API tokens" rows={4}>
          {(data) => (
            <>
              <SettingsSection
                title="MCP server"
                description="Connect Claude Code, Codex, Cursor or another AI assistant. It can do what you can do in the panel, with your role, and every change is in the audit log under your name and the token."
              >
                <div className="flex flex-col gap-4">
                  <CopyField value={data.mcp_url} label="the MCP address" />
                  <McpSetupGuide url={data.mcp_url} />
                  <p className="text-xs text-muted-foreground">
                    Create a token below: the next page shows these snippets with the token filled in.
                  </p>
                </div>
              </SettingsSection>
              <SettingsSection
                title="API tokens"
                description="Personal tokens for the MCP server and the REST API (Authorization: Bearer). A token acts as you; a read-only token cannot change anything."
                footer={
                  <>
                    <span>Revoke a token you no longer use.</span>
                    <LinkButton href="/settings/api/new" size="sm">
                      <PlusIcon />
                      Create token
                    </LinkButton>
                  </>
                }
              >
                <TokensTable tokens={data.items} onRevoke={setRevoking} />
              </SettingsSection>
            </>
          )}
        </QueryState>
      </div>
      <ConfirmDialog
        open={revoking !== null}
        onOpenChange={(open) => !open && setRevoking(null)}
        destructive
        title={`Revoke ${revoking?.name ?? "the token"}?`}
        description="Assistants and scripts using it stop working at once. This cannot be undone."
        confirmLabel="Revoke"
        pending={revoke.isPending}
        onConfirm={() => revoking && revoke.mutate(revoking.id, { onSuccess: () => setRevoking(null) })}
      />
    </>
  );
}
