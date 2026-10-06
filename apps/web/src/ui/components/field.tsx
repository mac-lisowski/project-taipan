"use client"

import * as React from "react"
import { cn } from "cn"
import { Input } from "./input"
import { Label } from "./label"

// The eyebrow Label + Input cluster the auth forms repeated; callers tune
// the wrapper via className, input props pass through untouched.
function Field({
  id,
  label,
  className,
  ...props
}: React.ComponentProps<"input"> & { label: string }) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <Label
        htmlFor={id}
        className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground"
      >
        {label}
      </Label>
      <Input id={id} className="h-10 font-sans text-sm" {...props} />
    </div>
  )
}

export { Field }
