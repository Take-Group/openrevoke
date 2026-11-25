"use client";

import { useState } from "react";

import { TextField } from "@/components/auth/form-parts";
import { CopyField } from "@/components/common/copy-button";
import { FormField } from "@/components/common/form-field";
import { Panel } from "@/components/common/panel";
import { Button } from "@/components/ui/button";
import { OptionSelect } from "@/components/common/option-select";
import { useCreateInvite } from "@/hooks/use-users";
import type { InviteCreated, UserRole } from "@/lib/api/auth-types";

const ROLE_OPTIONS = [
  { value: "user", label: "User" },
  { value: "admin", label: "Admin" },
];

function CreatedLink({ invite }: { invite: InviteCreated }) {
  return (
    <Panel className="max-w-lg" bodyClassName="flex flex-col gap-2 px-3 py-2.5 text-sm">
      <p>Pass this link to {invite.email} yourself (chat, phone); the panel sends no e-mail:</p>
      <CopyField value={invite.link} label="the link" />
      <p className="text-xs text-muted-foreground">The link works once. It is not shown again.</p>
    </Panel>
  );
}

/** Invite by e-mail: the person creates the account with the link and signs in. */
export function InviteForm() {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<UserRole>("user");
  const [created, setCreated] = useState<InviteCreated | null>(null);
  const invite = useCreateInvite();
  return (
    <div className="flex flex-col gap-3">
      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          invite.mutate(
            { email, role },
            {
              onSuccess: (data) => {
                setCreated(data);
                setEmail("");
              },
            },
          );
        }}
      >
        <TextField
          id="invite-email"
          label="E-mail"
          type="email"
          required
          placeholder="name@company.com"
          value={email}
          onValue={setEmail}
        />
        <FormField label="Role" htmlFor="invite-role" className="w-32">
          <OptionSelect id="invite-role" value={role} options={ROLE_OPTIONS} onChange={(next) => next && setRole(next as UserRole)} />
        </FormField>
        <Button type="submit" disabled={invite.isPending || !email}>
          Invite
        </Button>
      </form>
      {created && <CreatedLink invite={created} />}
    </div>
  );
}
