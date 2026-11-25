/**
 * Class lists shared by every form control and every floating list, so a
 * select, a searchable select, a person picker and an autocomplete look the
 * same as `Input` and as the menu items of `DropdownMenu` and `Command`.
 * Change the look here, not in the components.
 */

/** A button that opens a list, sized and bordered like `Input`. */
export const fieldTriggerClass =
  "flex h-9 w-full min-w-0 cursor-pointer items-center justify-between gap-2 rounded-lg border border-input bg-background py-1 pr-2.5 pl-3 text-left text-sm font-normal whitespace-nowrap transition-[color,background-color,border-color,box-shadow] outline-none select-none hover:border-ring/60 focus-visible:border-brand focus-visible:ring-4 focus-visible:ring-brand/15 data-popup-open:border-brand data-popup-open:ring-4 data-popup-open:ring-brand/15 disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-subtle disabled:opacity-60 data-disabled:pointer-events-none data-disabled:bg-subtle data-disabled:opacity-60 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 data-placeholder:text-faint [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4";

/** The floating panel of a select or an autocomplete. */
export const listPopupClass =
  "z-50 max-h-(--available-height) w-(--anchor-width) min-w-36 origin-(--transform-origin) overflow-x-hidden overflow-y-auto rounded-lg bg-popover p-1 text-popover-foreground shadow-popover outline-none duration-100 data-[side=bottom]:slide-in-from-top-2 data-[side=top]:slide-in-from-bottom-2 data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95";

/** One row of a floating list; the check mark sits in the right padding. */
export const listItemClass =
  "relative flex min-h-9 w-full cursor-pointer items-center gap-2.5 rounded-md py-1.5 pr-8 pl-2 text-sm outline-hidden select-none data-highlighted:bg-accent data-highlighted:text-foreground data-disabled:pointer-events-none data-disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4";
