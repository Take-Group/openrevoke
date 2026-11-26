"use client";

import { useEffect, useMemo } from "react";
import { ImageUpIcon, Trash2Icon } from "lucide-react";

import { AppAvatar } from "@/components/common/avatars";
import { FileButton } from "@/components/common/file-button";
import { FormField } from "@/components/common/form-field";
import { SuggestInput } from "@/components/common/suggest-input";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { APP_CATEGORIES } from "@/lib/api/inventory-types";

export const LOGO_ACCEPT = "image/png,image/jpeg,image/webp,image/svg+xml";
const LOGO_MAX_BYTES = 256 * 1024;

/** A logo file the API will take: an image under 256 KB (the API checks the content again). */
export function logoProblem(file: File): string | null {
  if (file.size > LOGO_MAX_BYTES) return "The logo is larger than 256 KB";
  if (!LOGO_ACCEPT.split(",").includes(file.type)) return "Use a PNG, JPEG, WebP or SVG image";
  return null;
}

interface WebsiteCategoryProps {
  idPrefix: string;
  website: string;
  category: string;
  onWebsite: (value: string) => void;
  onCategory: (value: string) => void;
}

/** Website and category of an app, side by side. Category is free text with the usual ones suggested. */
export function WebsiteCategoryFields({ idPrefix, website, category, onWebsite, onCategory }: WebsiteCategoryProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <FormField label="Website" htmlFor={`${idPrefix}-website`}>
        <Input
          id={`${idPrefix}-website`}
          type="url"
          placeholder="https://"
          value={website}
          onChange={(event) => onWebsite(event.target.value)}
        />
      </FormField>
      <FormField label="Category" htmlFor={`${idPrefix}-category`} info="Any word; used by the filter on Apps.">
        <SuggestInput
          id={`${idPrefix}-category`}
          value={category}
          onChange={onCategory}
          suggestions={APP_CATEGORIES}
          placeholder="e.g. design"
        />
      </FormField>
    </div>
  );
}

interface LogoPickerProps {
  name: string;
  /** The saved logo (`logo_url`), shown while no new file is picked. */
  current?: string | null;
  file: File | null;
  onFile: (file: File | null) => void;
  /** Shows "Remove" for a saved uploaded logo. */
  onRemove?: () => void;
  pending?: boolean;
}

/** Logo preview with "Upload" (PNG, JPEG, WebP, SVG up to 256 KB) and "Remove". */
export function LogoPicker({ name, current, file, onFile, onRemove, pending }: LogoPickerProps) {
  const preview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);
  useEffect(() => () => (preview ? URL.revokeObjectURL(preview) : undefined), [preview]);
  const uploaded = Boolean(current?.startsWith("/api/apps/"));

  return (
    <div className="flex items-center gap-3">
      <AppAvatar name={name || "?"} logoUrl={preview ?? current ?? null} size="lg" />
      <FileButton variant="outline" size="sm" accept={LOGO_ACCEPT} disabled={pending} onFile={onFile}>
        <ImageUpIcon />
        {file || uploaded ? "Replace" : "Upload"}
      </FileButton>
      {file && (
        <Button type="button" variant="ghost" size="sm" disabled={pending} onClick={() => onFile(null)}>
          Clear
        </Button>
      )}
      {!file && uploaded && onRemove && (
        <Button type="button" variant="ghost" size="sm" disabled={pending} onClick={onRemove}>
          <Trash2Icon />
          Remove
        </Button>
      )}
      <span className="text-xs text-muted-foreground">PNG, JPEG, WebP or SVG, up to 256 KB</span>
    </div>
  );
}
