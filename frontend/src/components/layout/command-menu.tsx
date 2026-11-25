"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";

import { AppAvatar, PersonAvatar } from "@/components/common/avatars";
import { NAV_PAGES } from "@/components/layout/nav-items";
import { THEMES } from "@/components/layout/theme-toggle";
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { useApps } from "@/hooks/use-apps";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { usePeople } from "@/hooks/use-people";
import { fullName } from "@/lib/format";

function matches(text: string, search: string): boolean {
  return text.toLowerCase().includes(search.trim().toLowerCase());
}

/**
 * Mounted only while the palette is open, so closed it costs no requests.
 * Filtering is ours (people come filtered from the server), and the first
 * result stays selected while the lists change, so Enter always opens it.
 */
function Palette({ go, close }: { go: (href: string) => void; close: () => void }) {
  const { setTheme } = useTheme();
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState("");
  const q = useDebouncedValue(search.trim(), 200);
  const people = usePeople({ q: q || undefined, limit: 8 });
  const apps = useApps({ limit: 500 });

  const pages = NAV_PAGES.filter((item) => matches(item.title, search));
  const appItems = (apps.data?.items ?? []).filter((app) => matches(`${app.name} ${app.slug}`, search)).slice(0, 8);
  const personItems = people.data?.items ?? [];
  const themes = THEMES.filter((theme) => matches(`${theme.label} theme`, search));

  const values = [
    ...pages.map((item) => `page:${item.href}`),
    ...personItems.map((person) => `person:${person.id}`),
    ...appItems.map((app) => `app:${app.id}`),
    ...themes.map((theme) => `theme:${theme.value}`),
  ];
  const value = values.includes(selected) ? selected : (values[0] ?? "");

  return (
    <Command shouldFilter={false} value={value} onValueChange={setSelected} loop>
      <CommandInput placeholder="Search pages, people, apps…" value={search} onValueChange={setSearch} />
      <CommandList className="max-h-96">
        <CommandEmpty>No results</CommandEmpty>
        {pages.length > 0 && (
          <CommandGroup heading="Pages">
            {pages.map((item) => (
              <CommandItem key={item.href} value={`page:${item.href}`} onSelect={() => go(item.href)}>
                <item.icon />
                {item.title}
              </CommandItem>
            ))}
          </CommandGroup>
        )}
        {personItems.length > 0 && (
          <CommandGroup heading="People">
            {personItems.map((person) => (
              <CommandItem key={person.id} value={`person:${person.id}`} onSelect={() => go(`/people/${person.id}`)}>
                <PersonAvatar firstName={person.first_name} lastName={person.last_name} email={person.primary_email} size="xs" />
                <span className="min-w-0 flex-1 truncate">{fullName(person)}</span>
                <span className="truncate text-xs text-muted-foreground">{person.primary_email}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        )}
        {appItems.length > 0 && (
          <CommandGroup heading="Apps">
            {appItems.map((app) => (
              <CommandItem key={app.id} value={`app:${app.id}`} onSelect={() => go(`/apps/${app.id}`)}>
                <AppAvatar name={app.name} slug={app.slug} connectorKey={app.connector_key} size="xs" />
                {app.name}
              </CommandItem>
            ))}
          </CommandGroup>
        )}
        {themes.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Theme">
              {themes.map(({ value: theme, label, icon: Icon }) => (
                <CommandItem
                  key={theme}
                  value={`theme:${theme}`}
                  onSelect={() => {
                    close();
                    setTheme(theme);
                  }}
                >
                  <Icon />
                  {label} theme
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}
      </CommandList>
    </Command>
  );
}

/** ⌘K palette: pages, people (server search), apps and the theme. */
export function CommandMenu({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const router = useRouter();

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        onOpenChange(!open);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onOpenChange]);

  const close = () => onOpenChange(false);
  const go = (href: string) => {
    close();
    router.push(href);
  };

  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Search"
      description="Go to a page, a person or an app"
      className="sm:max-w-xl"
    >
      {open && <Palette go={go} close={close} />}
    </CommandDialog>
  );
}
