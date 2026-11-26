import { PencilIcon } from "lucide-react";

import { PersonAvatar } from "@/components/common/avatars";
import { InfoTip } from "@/components/common/info-tip";
import { LinkButton, RecordLink } from "@/components/common/links";
import { Panel } from "@/components/common/panel";
import { fullName } from "@/lib/format";
import type { PersonDetail, PersonRef } from "@/lib/api/types";

function PersonLine({ person }: { person: PersonRef }) {
  return (
    <span className="flex min-w-0 items-center gap-2">
      <PersonAvatar firstName={person.first_name} lastName={person.last_name} email={person.primary_email} size="xs" />
      <RecordLink href={`/people/${person.person_id}`} className="truncate">
        {fullName(person)}
      </RecordLink>
      {person.status === "left" && <span className="text-xs text-muted-foreground">left</span>}
    </span>
  );
}

function Fact({ label, children }: { label: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <div className="mb-1 flex items-center gap-1 text-xs text-muted-foreground">{label}</div>
      <div className="min-w-0 truncate text-sm">{children}</div>
    </div>
  );
}

/** Manager, department, job title and the people who report to this person (`/people/[id]`). */
export function PersonManagerSection({ person }: { person: PersonDetail }) {
  const sourceNote =
    person.manager_source === "manual"
      ? "Set by an admin or a CSV import: syncs keep it."
      : "From the people source: the next sync may change it.";
  return (
    <Panel
      title="Reporting line"
      className="mb-6"
      actions={
        <LinkButton href={`/people/${person.id}/edit`} variant="ghost" size="sm">
          <PencilIcon />
          Edit
        </LinkButton>
      }
    >
      <div className="grid gap-4 px-5 py-4 sm:grid-cols-3">
        <Fact
          label={
            <>
              Manager
              <InfoTip>{`Approves this person's access requests. ${sourceNote}`}</InfoTip>
            </>
          }
        >
          {person.manager ? <PersonLine person={person.manager} /> : <span className="text-muted-foreground">No manager</span>}
        </Fact>
        <Fact label="Department">{person.department ?? <span className="text-muted-foreground">—</span>}</Fact>
        <Fact label="Job title">{person.job_title ?? <span className="text-muted-foreground">—</span>}</Fact>
      </div>
      {person.reports.length > 0 && (
        <div className="border-t px-5 py-4">
          <div className="mb-2 text-xs text-muted-foreground">
            Reports <span className="tabular-nums">{person.reports.length}</span>
          </div>
          <ul className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
            {person.reports.map((report) => (
              <li key={report.person_id} className="min-w-0">
                <PersonLine person={report} />
              </li>
            ))}
          </ul>
        </div>
      )}
    </Panel>
  );
}
