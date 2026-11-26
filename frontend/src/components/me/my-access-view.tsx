"use client";

import { KeyRoundIcon, PlusIcon, UserRoundXIcon } from "lucide-react";

import { AppAvatar } from "@/components/common/avatars";
import { EmptyState } from "@/components/common/empty-state";
import { LinkButton } from "@/components/common/links";
import { PageHeader } from "@/components/common/page-header";
import { Panel } from "@/components/common/panel";
import { QueryState } from "@/components/common/query-state";
import { RelativeTime } from "@/components/common/relative-time";
import { StatusBadge } from "@/components/common/status-badge";
import { FALLBACK_TEXT, RequestStatusBadge, waitingText } from "@/components/requests/request-parts";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useMyAccess } from "@/hooks/use-me";
import type { MyAccount, MyRequest } from "@/lib/api/me-types";
import type { AppRef } from "@/lib/api/types";
import { cn } from "@/lib/utils";

function AppCell({ app }: { app: AppRef }) {
  return (
    <div className="flex items-center gap-2.5">
      <AppAvatar name={app.name} slug={app.slug} logoUrl={app.logo_url} size="sm" />
      <span className="font-medium">{app.name}</span>
    </div>
  );
}

function Accounts({ accounts }: { accounts: MyAccount[] }) {
  if (accounts.length === 0) {
    return (
      <Panel title="Accounts">
        <EmptyState icon={KeyRoundIcon} title="No accounts yet" description="Apps where you have an account show up here." className="py-8" />
      </Panel>
    );
  }
  return (
    <Panel title="Accounts" meta={accounts.length}>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>App</TableHead>
            <TableHead className="max-md:hidden">Login</TableHead>
            <TableHead className="max-md:hidden">Role</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="max-md:hidden">Last seen</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {accounts.map((account) => (
            <TableRow key={account.account_id}>
              <TableCell>
                <AppCell app={account.app} />
              </TableCell>
              <TableCell className="text-muted-foreground max-md:hidden">{account.email ?? account.username ?? "—"}</TableCell>
              <TableCell className="capitalize max-md:hidden">{account.role ?? "—"}</TableCell>
              <TableCell>
                <StatusBadge status={account.status} />
              </TableCell>
              <TableCell className="max-md:hidden">
                <RelativeTime value={account.last_seen_at} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Panel>
  );
}

function requestNote(request: MyRequest): string {
  if (request.rejection_comment) return request.rejection_comment;
  if (request.fallback_reason && request.waiting_for === "admin") return FALLBACK_TEXT[request.fallback_reason];
  return request.justification ?? "—";
}

function Requests({ requests }: { requests: MyRequest[] }) {
  if (requests.length === 0) return null;
  return (
    <Panel title="Requests" meta={requests.length}>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>App</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="max-md:hidden">Waiting for</TableHead>
            <TableHead className="max-md:hidden">Note</TableHead>
            <TableHead className="max-md:hidden">Asked</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {requests.map((request) => (
            <TableRow key={request.request_id}>
              <TableCell>
                <AppCell app={request.app} />
              </TableCell>
              <TableCell>
                <RequestStatusBadge status={request.status} />
              </TableCell>
              <TableCell className="whitespace-nowrap text-muted-foreground max-md:hidden">{waitingText(request)}</TableCell>
              <TableCell
                className={cn("max-w-64 truncate max-md:hidden", request.rejection_comment ? "text-destructive" : "text-muted-foreground")}
                title={requestNote(request)}
              >
                {requestNote(request)}
              </TableCell>
              <TableCell className="max-md:hidden">
                <RelativeTime value={request.created_at} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Panel>
  );
}

/** `/me`: the signed-in user's own accounts and requests (the home page of a `user`). */
export function MyAccessView() {
  const access = useMyAccess();
  const canRequest = (access.data?.requestable_apps.length ?? 0) > 0;
  return (
    <>
      <PageHeader
        title="My access"
        actions={
          <LinkButton href="/me/request" size="sm" disabled={!canRequest} title={canRequest ? undefined : "No app to ask for"}>
            <PlusIcon />
            Request access
          </LinkButton>
        }
      />
      <QueryState query={access} feature="My access">
        {(data) =>
          data.person === null ? (
            <EmptyState
              icon={UserRoundXIcon}
              title="Your e-mail is not on the people list"
              description="Open Revoke finds your accounts by your e-mail. Ask an admin to add you, or to add this address as your alias."
            />
          ) : (
            <div className="flex flex-col gap-6">
              <Accounts accounts={data.accounts} />
              <Requests requests={data.requests} />
            </div>
          )
        }
      </QueryState>
    </>
  );
}
