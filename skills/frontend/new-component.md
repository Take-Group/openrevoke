# Skill: New Component

## What it does
Adds a new UI component following the shadcn/ui + CVA + Tailwind pattern used in this project.

## Files involved
- `src/components/ui/<name>.tsx` — primitive/reusable UI component
- `src/components/<name>.tsx` — composite/business component
- `src/lib/utils.ts` — `cn()` utility for className merging

## Flow
1. **Decide the component type**:
   - Primitive UI (button, card, input) → `src/components/ui/`
   - Business/feature component (user-card, order-list) → `src/components/`
2. **Create the component file**
3. **Add `"use client"` directive** if the component uses hooks, event handlers, or browser APIs
4. **Use CVA** for variant management if the component has multiple visual styles
5. **Use `cn()`** for safe className composition

## Example — primitive UI component
```tsx
// src/components/ui/badge.tsx
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-semibold",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground",
        secondary: "bg-secondary text-secondary-foreground",
        destructive: "bg-destructive text-destructive-foreground",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}
```

## Example — business component
```tsx
// src/components/user-card.tsx
import { Badge } from "@/components/ui/badge";

interface UserCardProps {
  name: string;
  role: string;
}

export function UserCard({ name, role }: UserCardProps) {
  return (
    <div className="rounded-lg border p-4">
      <h3 className="font-semibold">{name}</h3>
      <Badge variant="secondary">{role}</Badge>
    </div>
  );
}
```

## Look

First check the catalogue in `skills/frontend/ui-kit.md`: the component may
exist. A new one goes into that catalogue in the same change.

Ink on white, hairline borders, 14px text, radius 7-10px. Use the tokens
(`bg-subtle`, `border`, `shadow-popover`, `text-muted-foreground`), never
indigo or blue classes, and no icon inside a tinted tile. Wrap a block in
`common/panel.tsx` instead of nesting cards. Rules in
`skills/frontend/pages.md`, "Look rules".

## Interactive components

A component a person clicks needs all four states from `ui-kit.md`,
"Interactive states": pointer cursor, hover, keyboard focus ring,
disabled. Build it on a Base UI part or on `Button`, so focus and the role
come with it. Hover it and Tab to it in the running stack before you say
it is done.

## How to extend
- Check if shadcn/ui already has the component: `bunx shadcn@latest add <name>`
- Keep components small — if it grows past 200 lines, split into sub-components
- Props interface always explicitly typed (no `any`)
