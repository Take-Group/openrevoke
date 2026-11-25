# open-revoke/frontend/src/components/ui/

Low-level primitives (shadcn style, built on `@base-ui/react`), restyled to the panel's Vercel look. Pages seldom use them directly: reach for `common/` first, and read `open-revoke/skills/frontend/ui-kit.md` for the rules (no native controls, tokens only, no height or colour overrides in `className`).

- `avatar.tsx`: `Avatar`, `AvatarImage`, `AvatarFallback`, `AvatarGroup`, `AvatarGroupCount`, `AvatarBadge`. Prefer `AppAvatar` and `PersonAvatar`.
- `badge.tsx`: `Badge`, `badgeVariants`; `variant`: default, secondary, destructive, outline, ghost, link.
- `breadcrumb.tsx`: `Breadcrumb`, `BreadcrumbList`, `BreadcrumbItem`, `BreadcrumbLink`, `BreadcrumbPage`, `BreadcrumbSeparator`, `BreadcrumbEllipsis`.
- `button.tsx`: `Button`, `buttonVariants`; `variant`: default, outline, secondary, ghost, destructive, link, link-muted; `size`: default (36 px), xs, sm (32 px), lg (40 px), icon, icon-xs, icon-sm, icon-lg.
- `card.tsx`: `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardAction`, `CardContent`, `CardFooter`.
- `checkbox.tsx`: `Checkbox`. The only checkbox allowed.
- `command.tsx`: `Command`, `CommandDialog`, `CommandInput`, `CommandList`, `CommandEmpty`, `CommandGroup`, `CommandItem`, `CommandShortcut`, `CommandSeparator`. Base of `SearchableSelect` and the palette.
- `dialog.tsx`: `Dialog`, `DialogTrigger`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription`, `DialogFooter`, `DialogClose`, `DialogOverlay`, `DialogPortal`.
- `dropdown-menu.tsx`: `DropdownMenu`, `DropdownMenuTrigger`, `DropdownMenuContent`, `DropdownMenuItem`, `DropdownMenuCheckboxItem`, `DropdownMenuRadioGroup`, `DropdownMenuRadioItem`, `DropdownMenuLabel`, `DropdownMenuSeparator`, `DropdownMenuShortcut`, `DropdownMenuGroup`, `DropdownMenuSub`, `DropdownMenuSubTrigger`, `DropdownMenuSubContent`, `DropdownMenuPortal`.
- `field-styles.ts`: `fieldTriggerClass` (select-like trigger, same as `Input`), `listPopupClass` (floating list), `listItemClass` (list row). Change the look of every select here.
- `input-group.tsx`: `InputGroup`, `InputGroupAddon`, `InputGroupButton`, `InputGroupText`, `InputGroupInput`, `InputGroupTextarea`; an input with icons or buttons inside.
- `input.tsx`: `Input` (36 px, fixed look).
- `kbd.tsx`: `Kbd`, `KbdGroup` keyboard hints.
- `label.tsx`: `Label`.
- `popover.tsx`: `Popover`, `PopoverTrigger`, `PopoverContent`, `PopoverHeader`, `PopoverTitle`, `PopoverDescription`.
- `progress.tsx`: `Progress`, `ProgressTrack`, `ProgressIndicator`, `ProgressLabel`, `ProgressValue`.
- `scroll-area.tsx`: `ScrollArea`, `ScrollBar`.
- `select.tsx`: `Select`, `SelectTrigger`, `SelectValue`, `SelectContent`, `SelectItem`, `SelectGroup`, `SelectLabel`, `SelectSeparator`; `SelectRootProps`. Wrapped by `OptionSelect` in `common/`.
- `separator.tsx`: `Separator`.
- `sheet.tsx`: `Sheet`, `SheetTrigger`, `SheetContent`, `SheetHeader`, `SheetTitle`, `SheetDescription`, `SheetFooter`, `SheetClose`. Base of the phone sidebar; forms are pages (`FormPage`), not sheets.
- `sidebar.tsx`: large sidebar kit (`SidebarProvider`, `Sidebar`, `SidebarMenu`, `SidebarMenuButton`, `SidebarMenuSub`, `SidebarInset`, `SidebarTrigger`, `useSidebar`, ...). Used only by `layout/`.
- `skeleton.tsx`: `Skeleton` grey loading block.
- `sonner.tsx`: `Toaster` (mounted once in `providers.tsx`); call `toast` from `sonner` for messages.
- `switch.tsx`: `Switch`. Prefer `SwitchField`.
- `table.tsx`: `Table`, `TableHeader`, `TableBody`, `TableFooter`, `TableRow`, `TableHead`, `TableCell`, `TableCaption`. Lists use `DataTable` in `data-table/`.
- `tabs.tsx`: `Tabs`, `TabsList` (`variant`: default pill, line), `TabsTrigger`, `TabsContent`, `tabsListVariants`.
- `textarea.tsx`: `Textarea`.
- `toggle-group.tsx`: `ToggleGroup`, `ToggleGroupItem`.
- `toggle.tsx`: `Toggle`, `toggleVariants`.
- `tooltip.tsx`: `Tooltip`, `TooltipTrigger`, `TooltipContent`, `TooltipProvider`. Prefer `Hint` and `InfoTip`.
