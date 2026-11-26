"use client";

import { PlusIcon, UserMinusIcon, UserPlusIcon } from "lucide-react";

import { PersonAvatar } from "@/components/common/avatars";
import { DetailList, type DetailRow } from "@/components/common/detail-list";
import { LinkButton } from "@/components/common/links";
import { DetailHeader } from "@/components/common/page-header";
import { QueryState } from "@/components/common/query-state";
import { Stat, StatStrip } from "@/components/common/stat";
import { StatusBadge } from "@/components/common/status-badge";
import { PersonAccountsTable } from "@/components/people/person-accounts-table";
import { PersonKindBadge } from "@/components/people/person-kind-badge";
import { PersonManagerSection } from "@/components/people/person-manager-section";
import { PersonDiscoveredApps } from "@/components/people/person-discovered-apps";
import { PersonActivity } from "@/components/people/person-activity";
import { PersonMoreMenu } from "@/components/people/person-more-menu";
import { PersonProfilesSection } from "@/components/people/person-profiles-section";
import { PersonSourcesTable } from "@/components/people/person-sources-table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePerson } from "@/hooks/use-people";
import { useUrlTab } from "@/hooks/use-url-tab";
import { ConvertedTotal } from "@/components/common/converted-money";
import { DetailPageSkeleton } from "@/components/common/page-skeletons";
import { formatWhen, fullName } from "@/lib/format";
import type { PersonDetail } from "@/lib/api/types";
import { PersonRequestsSection } from "@/components/people/person-requests-section";

export type PersonTab = "accounts" | "sign-ins" | "activity" | "sources" | "details";

function Details({ person }: { person: PersonDetail }) {
  const rows: DetailRow[] = [
    ["E-mail", person.primary_email],
    ["Aliases", person.aliases.length > 0 ? person.aliases.map((alias) => alias.email).join(", ") : "—"],
    ["Employee code", person.employee_code ?? "—"],
    ["Left", person.left_at ? formatWhen(person.left_at) : "—"],
    ["Added", formatWhen(person.created_at)],
    ["Notes", <span key="n" className="whitespace-pre-wrap">{person.notes || "—"}</span>],
  ];
  return <DetailList rows={rows} className="max-w-2xl" />;
}

function PersonPage({ person, initialTab }: { person: PersonDetail; initialTab?: PersonTab }) {
  const [tab, setTab] = useUrlTab<PersonTab>(initialTab, "accounts");
  const base = `/people/${person.id}`;
  const left = person.status === "left";
  const live = person.accounts.filter((account) => account.status !== "removed").length;

  return (
    <>
      <DetailHeader
        avatar={
          <PersonAvatar firstName={person.first_name} lastName={person.last_name} email={person.primary_email} size="lg" />
        }
        title={fullName(person)}
        badges={
          <>
            <StatusBadge status={person.status} />
            <PersonKindBadge person={person} />
          </>
        }
        subtitle={person.primary_email}
        actions={
          <>
            <LinkButton href={`${base}/add-to-app`} variant="outline" disabled={left} title={left ? "The person has left" : undefined}>
              <PlusIcon />
              Add to app
            </LinkButton>
            <LinkButton href={`${base}/onboard`} variant="outline" disabled={left} title={left ? "The person has left" : undefined}>
              <UserPlusIcon />
              Onboard
            </LinkButton>
            <LinkButton href={`${base}/offboard`} variant="destructive">
              <UserMinusIcon />
              Offboard
            </LinkButton>
            <PersonMoreMenu person={person} />
          </>
        }
      />
      <StatStrip>
        <Stat label="Monthly cost">
          <ConvertedTotal total={person.monthly_cost_total} parts={person.monthly_cost} />
        </Stat>
        <Stat label="Accounts">
          {live}
        </Stat>
        <Stat label="Apps">
          {person.apps.length}
        </Stat>
        <Stat label="Added">
          {formatWhen(person.created_at).split(",")[0]}
        </Stat>
      </StatStrip>
      <PersonManagerSection person={person} />
      <PersonProfilesSection person={person} />
      <Tabs value={tab} onValueChange={(value) => setTab(value as PersonTab)}>
        <TabsList variant="line" className="mb-3">
          <TabsTrigger value="accounts">
            Accounts <span className="text-muted-foreground tabular-nums">{person.accounts.length}</span>
          </TabsTrigger>
          <TabsTrigger value="sign-ins">Google sign-ins</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
          <TabsTrigger value="sources">
            Sources <span className="text-muted-foreground tabular-nums">{person.sources.length}</span>
          </TabsTrigger>
          <TabsTrigger value="details">Details</TabsTrigger>
        </TabsList>
        <TabsContent value="accounts">
          <PersonAccountsTable person={person} />
        </TabsContent>
        <TabsContent value="sign-ins">
          <PersonDiscoveredApps personId={person.id} />
        </TabsContent>
        <TabsContent value="activity">
          <PersonActivity personId={person.id} />
        </TabsContent>
        <TabsContent value="sources">
          <PersonSourcesTable sources={person.sources} />
        </TabsContent>
        <TabsContent value="details">
          <Details person={person} />
        </TabsContent>
      </Tabs>
      <PersonRequestsSection personId={person.id} />
    </>
  );
}

export function PersonDetailView({ id, initialTab }: { id: string; initialTab?: PersonTab }) {
  const query = usePerson(id);
  return (
    <QueryState query={query} loading={<DetailPageSkeleton stats={4} tabs={5} />}>
      {(person) => <PersonPage person={person} initialTab={initialTab} />}
    </QueryState>
  );
}
