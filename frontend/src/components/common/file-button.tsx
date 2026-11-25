"use client";

import { useRef } from "react";

import { Button } from "@/components/ui/button";

type ButtonProps = React.ComponentProps<typeof Button>;

interface FileButtonProps extends Omit<ButtonProps, "onClick" | "type"> {
  /** File types for the picker, e.g. "image/png,image/jpeg". */
  accept?: string;
  onFile: (file: File) => void;
}

/** A button that opens the file picker (e.g. "Upload" an icon). For a form field use `FileDrop`. */
export function FileButton({ accept, onFile, children, ...buttonProps }: FileButtonProps) {
  const input = useRef<HTMLInputElement>(null);
  return (
    <>
      <input
        ref={input}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onFile(file);
          event.target.value = "";
        }}
      />
      <Button type="button" {...buttonProps} onClick={() => input.current?.click()}>
        {children}
      </Button>
    </>
  );
}
