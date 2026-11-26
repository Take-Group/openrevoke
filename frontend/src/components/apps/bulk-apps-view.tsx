"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { CatalogItemLabel } from "@/components/common/catalog-app-picker";
import { FormField } from "@/components/common/form-field";
import { FormPage } from "@/components/common/form-page";
import { LinkButton } from "@/components/common/links";
import { LoadingRows } from "@/components/common/query-state";
import { SearchInput } from "@/components/common/search-input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { useCreateApps } from "@/hooks/use-apps";
import { useCatalogSearch } from "@/hooks/use-catalog";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import type { CatalogSearchItem } from "@/lib/api/catalog-types";
import { cn } from "@/lib/utils";

const GRID_SIZE = 48;

function ownNames(text: string): string[] {
  return [...new Set(text.split(/[\n,;]+/).map((name) => name.trim()).filter(Boolean))];
}

/** One catalog app in the grid: a card that ticks; added apps are shown but cannot be ticked. */
function CatalogCard({ item, checked, onToggle }: { item: CatalogSearchItem; checked: boolean; onToggle: () => void }) {
  const disabled = Boolean(item.already_added);
  return (
    <label
      className={cn(
        "flex items-center gap-2.5 rounded-lg border bg-card px-3 py-2.5 text-sm transition-colors",
        disabled ? "opacity-60" : "cursor-pointer hover:bg-subtle",
        checked && "border-brand bg-brand-soft hover:bg-brand-soft",
      )}
    >
      <Checkbox checked={checked} disabled={disabled} onCheckedChange={onToggle} aria-label={item.name} />
      <CatalogItemLabel item={item} />
    </label>
  );
}

/**
 * `/apps/new/bulk` ("Add several apps"): a grid of catalog apps, apps discovery found and nobody
 * tracks first, with search; ticked apps and typed names are added in one save as manual, free apps.
 */
export function BulkAppsView() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [picked, setPicked] = useState<Map<string, CatalogSearchItem>>(new Map());
  const [names, setNames] = useState("");
  const q = useDebouncedValue(search.trim(), 200);
  const grid = useCatalogSearch(q, GRID_SIZE);
  const create = useCreateApps();
  const own = ownNames(names);
  const count = picked.size + own.length;

  const toggle = (item: CatalogSearchItem) =>
    setPicked((current) => {
      const next = new Map(current);
      if (next.has(item.slug)) next.delete(item.slug);
      else next.set(item.slug, item);
      return next;
    });

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (count === 0) return;
    const apps = [...[...picked.keys()].map((slug) => ({ catalog_key: slug })), ...own.map((name) => ({ name }))];
    create.mutate(apps, { onSuccess: () => router.push("/apps") });
  };

  // Ticked apps stay on screen while the search shows others.
  // Apps already added go last: they are there to show, not to tick.
  const shown = [...(grid.data?.items ?? [])].sort((a, b) => Number(Boolean(a.already_added)) - Number(Boolean(b.already_added)));
  const hiddenPicked = [...picked.values()].filter((item) => !shown.some((entry) => entry.slug === item.slug));

  return (
    <FormPage
      title="Add several apps"
      backHref="/apps"
      backLabel="Apps"
      wide
      onSubmit={submit}
      submitLabel="Add apps"
      hint="Added as manual, free apps"
      actions={
        <>
          <LinkButton href="/apps" variant="outline">
            Cancel
          </LinkButton>
          <Button type="submit" disabled={count === 0 || create.isPending}>
            {create.isPending ? "Saving…" : count === 0 ? "Add apps" : `Add ${count} app${count === 1 ? "" : "s"}`}
          </Button>
        </>
      }
    >
      <SearchInput placeholder="Search the catalog" value={search} onChange={setSearch} />
      {hiddenPicked.length > 0 && (
        <p className="text-xs text-muted-foreground">Also ticked: {hiddenPicked.map((item) => item.name).join(", ")}</p>
      )}
      {grid.isLoading ? (
        <LoadingRows rows={4} />
      ) : shown.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Not in the catalog: type its name below.</p>
      ) : (
        <div className={cn("grid max-h-[28rem] gap-2 overflow-y-auto sm:grid-cols-2", grid.isFetching && "opacity-80")}>
          {shown.map((item) => (
            <CatalogCard key={item.slug} item={item} checked={picked.has(item.slug)} onToggle={() => toggle(item)} />
          ))}
        </div>
      )}
      <FormField
        label="Apps not in the catalog"
        htmlFor="own-apps"
        info="One per line or separated with commas. Apps that already exist are skipped."
      >
        <Textarea
          id="own-apps"
          rows={3}
          placeholder={"Internal CRM\nWarehouse system"}
          value={names}
          onChange={(event) => setNames(event.target.value)}
        />
      </FormField>
    </FormPage>
  );
}
