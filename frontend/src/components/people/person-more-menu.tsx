"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  CopyIcon,
  HistoryIcon,
  MoreHorizontalIcon,
  PencilIcon,
  ServerCogIcon,
  Trash2Icon,
  UserIcon,
} from "lucide-react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useDeletePerson, useSetPersonKind } from "@/hooks/use-people";
import { fullName } from "@/lib/format";
import type { PersonDetail } from "@/lib/api/types";

/** Edit, history, copy e-mail and Delete (only for a person without accounts and actions). */
export function PersonMoreMenu({ person }: { person: PersonDetail }) {
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const remove = useDeletePerson(person.id);
  const setKind = useSetPersonKind(person.id);

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger render={<Button variant="outline" size="icon" aria-label="More" />}>
          <MoreHorizontalIcon />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuItem onClick={() => router.push(`/people/${person.id}/edit`)}>
            <PencilIcon />
            Edit
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => router.push(`/audit?person=${person.id}`)}>
            <HistoryIcon />
            History
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={() => navigator.clipboard.writeText(person.primary_email).then(() => toast.success("E-mail copied"))}
          >
            <CopyIcon />
            Copy e-mail
          </DropdownMenuItem>
          <DropdownMenuItem
            disabled={setKind.isPending}
            onClick={() => setKind.mutate(person.kind === "service" ? "human" : "service")}
          >
            {person.kind === "service" ? <UserIcon /> : <ServerCogIcon />}
            {person.kind === "service" ? "Mark as person" : "Mark as service account"}
          </DropdownMenuItem>
          {person.can_delete && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem variant="destructive" onClick={() => setConfirming(true)}>
                <Trash2Icon />
                Delete
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title={`Delete ${fullName(person)}?`}
        description="No accounts and no actions, so nothing else changes. The audit log keeps the entry."
        confirmLabel="Delete"
        destructive
        pending={remove.isPending}
        onConfirm={() => remove.mutate(undefined, { onSuccess: () => router.push("/people") })}
      />
    </>
  );
}
