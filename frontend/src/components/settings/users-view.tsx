"use client";

import { CheckIcon, KeyRoundIcon, LinkIcon, MailIcon, Trash2Icon, UserCogIcon } from "lucide-react";
import { useState } from "react";

import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { CopyField } from "@/components/common/copy-button";
import { EmptyState } from "@/components/common/empty-state";
import { PageHeader, SETTINGS_COLUMN } from "@/components/common/page-header";
import { Panel } from "@/components/common/panel";
import { QueryState } from "@/components/common/query-state";
import { RelativeTime } from "@/components/common/relative-time";
import { StatusBadge, TagBadge } from "@/components/common/status-badge";
import { InviteForm } from "@/components/settings/invite-form";
import { SettingsSection } from "@/components/settings/settings-section";
import { SignupSettings } from "@/components/settings/signup-settings";
import { RowActions } from "@/components/data-table/row-actions";
import { DropdownMenuItem, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAuthState } from "@/hooks/use-auth";
import {
  useApproveUser,
  useCreateResetLink,
  useInvites,
  useRemoveUser,
  useResetUserTotp,
  useRevokeInvite,
  useUpdateUserRole,
  useUsers,
} from "@/hooks/use-users";
import type { UserOut } from "@/lib/api/auth-types";
import { cn } from "@/lib/utils";

type Pending = { kind: "remove" | "reset-totp" | "reject" | "reset-link"; user: UserOut } | null;

/** Sign-ups waiting for an admin: approve (then tell them they can sign in) or reject. */
function WaitingUsers({ users, onAsk }: { users: UserOut[]; onAsk: (p: Pending) => void }) {
  const approve = useApproveUser();
  return (
    <SettingsSection title="Waiting for approval" description="People who signed up on their own. Approve them to let them sign in as users.">
      <Panel>
        <Table>
          <TableBody>
            {users.map((user) => (
              <TableRow key={user.user_id}>
                <TableCell>
                  <div className="font-medium">{user.name}</div>
                  <div className="text-xs text-muted-foreground">{user.email}</div>
                </TableCell>
                <TableCell className="max-md:hidden">
                  <StatusBadge status={user.status} />
                </TableCell>
                <TableCell className="max-md:hidden">
                  <RelativeTime value={user.created_at} />
                </TableCell>
                <TableCell>
                  <div className="flex justify-end gap-2">
                    <Button variant="ghost" size="sm" onClick={() => onAsk({ kind: "reject", user })}>
                      Reject
                    </Button>
                    <Button size="sm" disabled={approve.isPending} onClick={() => approve.mutate(user.user_id)}>
                      <CheckIcon />
                      Approve
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Panel>
    </SettingsSection>
  );
}

function UsersTable({ users, me, onAsk }: { users: UserOut[]; me: string; onAsk: (p: Pending) => void }) {
  const role = useUpdateUserRole();
  return (
    <Panel>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>User</TableHead>
            <TableHead>Role</TableHead>
            <TableHead className="max-md:hidden">2FA</TableHead>
            <TableHead className="max-md:hidden">Last sign-in</TableHead>
            <TableHead className="w-px" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {users.map((user) => (
            <TableRow key={user.user_id}>
              <TableCell>
                <div className="font-medium">
                  {user.name}
                  {user.user_id === me && <span className="ml-1.5 text-xs text-muted-foreground">(you)</span>}
                </div>
                <div className="text-xs text-muted-foreground">{user.email}</div>
              </TableCell>
              <TableCell>
                <TagBadge className="capitalize">{user.role}</TagBadge>
              </TableCell>
              <TableCell className="max-md:hidden">
                <StatusBadge
                  status={user.totp_enabled ? "on" : "off"}
                  label={user.totp_enabled ? "On" : "Not set up"}
                  tone={user.totp_enabled ? "success" : "warning"}
                />
              </TableCell>
              <TableCell className="max-md:hidden">
                <RelativeTime value={user.last_login_at} />
              </TableCell>
              <TableCell className="text-right">
                <RowActions label={`Actions for ${user.name}`}>
                  <DropdownMenuItem
                    disabled={role.isPending}
                    onClick={() => role.mutate({ userId: user.user_id, role: user.role === "admin" ? "user" : "admin" })}
                  >
                    <UserCogIcon />
                    {user.role === "admin" ? "Make user" : "Make admin"}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => onAsk({ kind: "reset-link", user })}>
                    <LinkIcon />
                    Password reset link
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => onAsk({ kind: "reset-totp", user })}>
                    <KeyRoundIcon />
                    Reset 2FA
                  </DropdownMenuItem>
                  {user.user_id !== me && (
                    <>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem variant="destructive" onClick={() => onAsk({ kind: "remove", user })}>
                        <Trash2Icon />
                        Remove user
                      </DropdownMenuItem>
                    </>
                  )}
                </RowActions>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Panel>
  );
}

function OpenInvites() {
  const invites = useInvites();
  const revoke = useRevokeInvite();
  return (
    <QueryState query={invites} feature="Invites" rows={2}>
      {(data) => (
        <Panel>
          {data.items.length === 0 ? (
            <EmptyState icon={MailIcon} title="No open invites" className="py-8" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>E-mail</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead className="max-md:hidden">Expires</TableHead>
                  <TableHead className="w-px" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((invite) => (
                  <TableRow key={invite.invite_id}>
                    <TableCell>{invite.email}</TableCell>
                    <TableCell>
                      <TagBadge className="capitalize">{invite.role}</TagBadge>
                    </TableCell>
                    <TableCell className="max-md:hidden">
                      <RelativeTime value={invite.expires_at} />
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" disabled={revoke.isPending} onClick={() => revoke.mutate(invite.invite_id)}>
                        Revoke
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Panel>
      )}
    </QueryState>
  );
}

const CONFIRM: Record<NonNullable<Pending>["kind"], { title: (name: string) => string; description: string; label: string }> = {
  "reset-link": {
    title: (name) => `Create a password reset link for ${name}?`,
    description:
      "You get a one-time link to pass on yourself (chat, phone); nothing is e-mailed. It works for 24 hours, and older reset links stop working.",
    label: "Create link",
  },
  remove: {
    title: (name) => `Remove ${name}?`,
    description: "The user is signed out and can no longer sign in. The audit log keeps their changes.",
    label: "Remove",
  },
  "reset-totp": {
    title: (name) => `Reset 2FA of ${name}?`,
    description: "Use it when the phone is lost. The user is signed out and sets up a new authenticator at the next sign-in.",
    label: "Reset 2FA",
  },
  reject: {
    title: (name) => `Reject ${name}?`,
    description: "The sign-up is deleted. They can sign up again later, and you decide again.",
    label: "Reject",
  },
};

/** Who can sign in to the panel (admins only): sign-ups to approve, users, invites and the sign-up rules. */
export function UsersView() {
  const me = useAuthState().data?.user;
  const users = useUsers();
  const [pending, setPending] = useState<Pending>(null);
  const remove = useRemoveUser();
  const resetTotp = useResetUserTotp();
  const resetLink = useCreateResetLink();
  const [link, setLink] = useState<{ name: string; url: string } | null>(null);
  const active = users.data?.filter((user) => user.status === "active") ?? [];
  const waiting = users.data?.filter((user) => user.status !== "active") ?? [];

  const confirm = () => {
    if (!pending) return;
    if (pending.kind === "reset-link") {
      const name = pending.user.name;
      resetLink.mutate(pending.user.user_id, {
        onSuccess: (created) => {
          setPending(null);
          setLink({ name, url: created.link });
        },
      });
      return;
    }
    const mutation = pending.kind === "reset-totp" ? resetTotp : remove;
    mutation.mutate(pending.user.user_id, { onSuccess: () => setPending(null) });
  };

  return (
    <>
      <PageHeader title="Users" meta={users.data ? active.length : undefined} />
      <div className={cn(SETTINGS_COLUMN, "flex flex-col gap-10")}>
        {waiting.length > 0 && <WaitingUsers users={waiting} onAsk={setPending} />}
        <QueryState query={users} feature="Users">
          {() => <UsersTable users={active} me={me?.user_id ?? ""} onAsk={setPending} />}
        </QueryState>
        <div>
          <SettingsSection title="Sign-up" description="Whether people can create an account themselves, and who gets in without you.">
            <SignupSettings />
          </SettingsSection>
          <SettingsSection title="Invite a user" description="They create their account with the link and sign in at once.">
            <InviteForm />
          </SettingsSection>
          <SettingsSection title="Open invites" description="Links that were not used yet.">
            <OpenInvites />
          </SettingsSection>
        </div>
      </div>
      <ConfirmDialog
        open={pending !== null}
        onOpenChange={(open) => !open && setPending(null)}
        destructive={pending?.kind === "remove" || pending?.kind === "reject"}
        title={CONFIRM[pending?.kind ?? "remove"].title(pending?.user.name ?? "")}
        description={CONFIRM[pending?.kind ?? "remove"].description}
        confirmLabel={CONFIRM[pending?.kind ?? "remove"].label}
        pending={remove.isPending || resetTotp.isPending || resetLink.isPending}
        onConfirm={confirm}
      />
      <ConfirmDialog
        open={link !== null}
        onOpenChange={(open) => !open && setLink(null)}
        title={`Reset link for ${link?.name ?? ""}`}
        description="Pass this link to them. It works once, for 24 hours, and is not shown again."
        confirmLabel="Done"
        onConfirm={() => setLink(null)}
      >
        {link && <CopyField value={link.url} label="the link" />}
      </ConfirmDialog>
    </>
  );
}
