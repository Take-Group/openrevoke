"use client";

import { useState } from "react";
import type { LucideIcon } from "lucide-react";

import { useAppCatalog } from "@/hooks/use-catalog";
import { findBrand, luminance } from "@/lib/brand-icons";
import { cn } from "@/lib/utils";

type AvatarSize = "xs" | "sm" | "md" | "lg";

const SIZE: Record<AvatarSize, string> = {
  xs: "size-5 text-[0.6rem] [&_svg]:size-3",
  sm: "size-6 text-[0.65rem] [&_svg]:size-3.5",
  md: "size-8 text-xs [&_svg]:size-4",
  lg: "size-11 text-sm [&_svg]:size-6",
};

// Initials sit on a quiet neutral fill; colour is left to real brand marks.
const NEUTRAL = "bg-accent text-foreground/70 ring-1 ring-inset ring-border dark:bg-muted dark:text-foreground/80";

function initials(text: string, letters = 2): string {
  const words = text.trim().split(/[\s._@-]+/).filter(Boolean);
  if (words.length === 0) return "?";
  const chars = words.length === 1 ? [...words[0]].slice(0, letters) : words.slice(0, letters).map((word) => word[0]);
  return chars.join("").toUpperCase();
}

interface AppAvatarProps {
  name: string;
  slug?: string | null;
  connectorKey?: string | null;
  /** Slug in the API's app catalog, when the API matched the app (discovery matches by OAuth client). */
  catalogSlug?: string | null;
  size?: AvatarSize;
  className?: string;
}

/**
 * App mark, first that exists: the bundled brand icon (simple-icons), the logo from the API's app
 * catalog (a picture on a white tile, as app stores show them), initials.
 */
export function AppAvatar({ name, slug, connectorKey, catalogSlug, size = "md", className }: AppAvatarProps) {
  const catalog = useAppCatalog()(catalogSlug, slug, name);
  const brand = findBrand(connectorKey, catalog?.slug, slug, name);
  const [broken, setBroken] = useState<string | null>(null);
  const base = cn(
    "inline-flex shrink-0 items-center justify-center rounded-md border bg-background font-semibold select-none dark:bg-muted/50",
    SIZE[size],
    className,
  );

  const icon = brand && "icon" in brand ? brand.icon : null;
  if (icon && "parts" in icon) {
    return (
      <span className={base} title={name}>
        <svg role="img" aria-label={name} viewBox="0 0 24 24">
          {icon.parts.map((part) => (
            <path key={part.hex} d={part.path} style={{ fill: `#${part.hex}` }} />
          ))}
        </svg>
      </span>
    );
  }
  if (icon) {
    // Near-black marks (GitHub, Notion, Vercel) follow the text colour, so they show in dark mode.
    const dark = luminance(icon.hex) < 0.05;
    return (
      <span className={base} title={name}>
        <svg
          role="img"
          aria-label={name}
          viewBox="0 0 24 24"
          className={dark ? "fill-foreground" : undefined}
          style={dark ? undefined : { fill: `#${icon.hex}` }}
        >
          <path d={icon.path} />
        </svg>
      </span>
    );
  }
  const logo = !icon && catalog?.logo_url && broken !== catalog.logo_url ? catalog.logo_url : null;
  if (logo) {
    return (
      <span className={cn(base, "overflow-hidden bg-white p-px dark:bg-white")} title={name}>
        {/* eslint-disable-next-line @next/next/no-img-element -- a small bundled PNG from the API, no resizing needed */}
        <img
          src={logo}
          alt={name}
          loading="lazy"
          decoding="async"
          className="size-full rounded-[inherit] object-contain"
          onError={() => setBroken(logo)}
        />
      </span>
    );
  }
  // A brand without a bundled icon: its initial in the brand colour, or ink when the colour is too dark.
  const color = brand && "color" in brand ? brand.color : null;
  const ink = !color || luminance(color) < 0.05;
  return (
    <span
      className={cn(base, ink && "text-foreground/75")}
      style={ink ? undefined : { color: color }}
      title={name}
    >
      {initials(name, 1)}
    </span>
  );
}

/** A generic choice (a file, by hand, none) in the same hairline square as `AppAvatar`. */
export function GlyphAvatar({ icon: Icon, size = "md", className }: { icon: LucideIcon; size?: AvatarSize; className?: string }) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-md border bg-background text-muted-foreground dark:bg-muted/50",
        SIZE[size],
        className,
      )}
    >
      <Icon />
    </span>
  );
}

interface PersonAvatarProps {
  firstName: string;
  lastName: string;
  email?: string;
  size?: AvatarSize;
  className?: string;
}

export function PersonAvatar({ firstName, lastName, email, size = "md", className }: PersonAvatarProps) {
  const name = `${firstName} ${lastName}`.trim() || email || "?";
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full font-medium select-none",
        SIZE[size],
        NEUTRAL,
        className,
      )}
      aria-hidden
    >
      {initials(name)}
    </span>
  );
}
