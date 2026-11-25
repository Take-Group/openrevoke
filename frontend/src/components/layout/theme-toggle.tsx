"use client";

import { MonitorIcon, MoonIcon, SunIcon } from "lucide-react";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";

import {
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
} from "@/components/ui/dropdown-menu";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { cn } from "@/lib/utils";

export const THEMES = [
  { value: "light", label: "Light", icon: SunIcon },
  { value: "dark", label: "Dark", icon: MoonIcon },
  { value: "system", label: "System", icon: MonitorIcon },
] as const;

/** "Theme" submenu for a dropdown; CSS picks the sun or moon icon, so there is no flash. */
export function ThemeSubmenu() {
  const { theme, setTheme } = useTheme();
  return (
    <DropdownMenuSub>
      <DropdownMenuSubTrigger>
        <SunIcon className="dark:hidden" />
        <MoonIcon className="hidden dark:block" />
        Theme
      </DropdownMenuSubTrigger>
      <DropdownMenuSubContent className="w-36">
        <DropdownMenuRadioGroup value={theme ?? "system"} onValueChange={(value) => setTheme(String(value))}>
          {THEMES.map(({ value, label, icon: Icon }) => (
            <DropdownMenuRadioItem key={value} value={value}>
              <Icon />
              {label}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuSubContent>
    </DropdownMenuSub>
  );
}

const noSubscribe = () => () => {};

/**
 * Light, dark or system as a round three-icon switch (Vercel's footer), for pages without the
 * sidebar: sign-in, registration and the first run. The panel uses `ThemeSubmenu` in the user menu.
 * The chosen icon shows only after mount: the server does not know the theme.
 */
export function ThemeSwitch({ className }: { className?: string }) {
  const { theme, setTheme } = useTheme();
  const mounted = useSyncExternalStore(noSubscribe, () => true, () => false);
  const value = mounted ? (theme ?? "system") : null;
  return (
    <ToggleGroup
      aria-label="Theme"
      value={value ? [value] : []}
      onValueChange={(next) => next[0] && setTheme(String(next[0]))}
      spacing={0}
      className={cn("h-8 gap-0.5 rounded-full border bg-background p-[3px]", className)}
    >
      {THEMES.map(({ value: option, label, icon: Icon }) => (
        <ToggleGroupItem
          key={option}
          value={option}
          aria-label={label}
          title={label}
          className="size-6.5 min-w-0 rounded-full! border-0! p-0 text-faint hover:bg-transparent hover:text-foreground data-pressed:bg-accent data-pressed:text-foreground [&_svg]:size-3.5"
        >
          <Icon />
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  );
}
