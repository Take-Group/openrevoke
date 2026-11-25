"use client";

import { useState } from "react";
import { FileUpIcon } from "lucide-react";

import { cn } from "@/lib/utils";

interface FileDropProps {
  id?: string;
  /** File types for the picker, e.g. ".csv,text/csv". */
  accept?: string;
  /** What to drop, e.g. "the client JSON file". */
  what: string;
  /** Name of the chosen file; shown instead of the prompt. */
  fileName?: string | null;
  icon?: React.ReactNode;
  disabled?: boolean;
  onFile: (file: File | undefined) => void;
}

/**
 * A file field: drop a file on the dashed box or click it to pick one. Use instead of
 * `<input type="file">` or `<Input type="file">`, which the browser draws in its own style.
 */
export function FileDrop({ id, accept, what, fileName, icon, disabled, onFile }: FileDropProps) {
  const [over, setOver] = useState(false);
  return (
    <label
      htmlFor={id}
      aria-disabled={disabled || undefined}
      className={cn(
        "flex cursor-pointer flex-col items-center gap-1.5 rounded-lg border border-dashed border-input bg-card px-4 py-5 text-center text-sm text-muted-foreground transition-colors hover:border-brand/60 hover:bg-subtle focus-within:border-brand focus-within:ring-4 focus-within:ring-brand/15",
        over && "border-brand bg-brand-soft/40",
        disabled && "pointer-events-none opacity-60",
      )}
      onDragOver={(event) => {
        event.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(event) => {
        event.preventDefault();
        setOver(false);
        if (!disabled) onFile(event.dataTransfer.files[0]);
      }}
    >
      <span className="text-faint [&_svg]:size-5">{icon ?? <FileUpIcon />}</span>
      {fileName ? (
        <span className="font-medium text-foreground">{fileName}</span>
      ) : (
        <span>
          Drop {what} here or{" "}
          <span className="font-medium text-foreground underline decoration-brand/40 underline-offset-4">choose it</span>
        </span>
      )}
      <input
        id={id}
        type="file"
        accept={accept}
        disabled={disabled}
        className="sr-only"
        onChange={(event) => {
          onFile(event.target.files?.[0]);
          event.target.value = "";
        }}
      />
    </label>
  );
}
