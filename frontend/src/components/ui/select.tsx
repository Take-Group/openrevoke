"use client";

import * as React from "react";
import { Select as SelectPrimitive } from "@base-ui/react/select";
import { CheckIcon, ChevronDownIcon } from "lucide-react";

import { fieldTriggerClass, listItemClass, listPopupClass } from "@/components/ui/field-styles";
import { cn } from "@/lib/utils";

/** Select primitives on Base UI. Pages use `OptionSelect` from `common/option-select.tsx`. */
const Select = SelectPrimitive.Root;

function SelectTrigger({ className, children, ...props }: SelectPrimitive.Trigger.Props) {
  return (
    <SelectPrimitive.Trigger data-slot="select-trigger" className={cn(fieldTriggerClass, className)} {...props}>
      {children}
      <SelectPrimitive.Icon render={<ChevronDownIcon className="text-muted-foreground" />} />
    </SelectPrimitive.Trigger>
  );
}

function SelectValue({ className, ...props }: SelectPrimitive.Value.Props) {
  return <SelectPrimitive.Value data-slot="select-value" className={cn("min-w-0 flex-1 truncate", className)} {...props} />;
}

function SelectContent({
  className,
  children,
  side = "bottom",
  sideOffset = 4,
  align = "start",
  ...props
}: SelectPrimitive.Popup.Props & Pick<SelectPrimitive.Positioner.Props, "align" | "side" | "sideOffset">) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Positioner
        side={side}
        sideOffset={sideOffset}
        align={align}
        alignItemWithTrigger={false}
        className="isolate z-50"
      >
        <SelectPrimitive.Popup data-slot="select-content" className={cn(listPopupClass, className)} {...props}>
          <SelectPrimitive.List>{children}</SelectPrimitive.List>
        </SelectPrimitive.Popup>
      </SelectPrimitive.Positioner>
    </SelectPrimitive.Portal>
  );
}

function SelectItem({ className, children, ...props }: SelectPrimitive.Item.Props) {
  return (
    <SelectPrimitive.Item data-slot="select-item" className={cn(listItemClass, className)} {...props}>
      <SelectPrimitive.ItemText className="min-w-0 flex-1 truncate">{children}</SelectPrimitive.ItemText>
      <SelectPrimitive.ItemIndicator render={<span className="absolute right-2 flex size-4 items-center justify-center" />}>
        <CheckIcon />
      </SelectPrimitive.ItemIndicator>
    </SelectPrimitive.Item>
  );
}

function SelectGroup({ className, ...props }: SelectPrimitive.Group.Props) {
  return <SelectPrimitive.Group data-slot="select-group" className={cn(className)} {...props} />;
}

function SelectLabel({ className, ...props }: SelectPrimitive.GroupLabel.Props) {
  return (
    <SelectPrimitive.GroupLabel
      data-slot="select-label"
      className={cn("px-2 py-1.5 text-xs font-medium text-muted-foreground", className)}
      {...props}
    />
  );
}

function SelectSeparator({ className, ...props }: SelectPrimitive.Separator.Props) {
  return <SelectPrimitive.Separator data-slot="select-separator" className={cn("-mx-1 my-1 h-px bg-border", className)} {...props} />;
}

export type SelectRootProps = React.ComponentProps<typeof SelectPrimitive.Root>;

export { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectSeparator, SelectTrigger, SelectValue };
