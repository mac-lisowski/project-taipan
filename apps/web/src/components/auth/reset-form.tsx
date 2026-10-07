"use client";

import Link from "next/link";
import { useState, type FormEvent, type ReactNode } from "react";
import { Button, Field } from "@/ui";
import { RESET_LANDING, submitReset } from "@/lib/reset-password";

// Reset form from the mailed link: one password field, upstream errors
// verbatim, success assigns to the dashboard landing so the fresh
// session cookie (re-emitted by the BFF) drives the private layout.
// The token stays fixed for a corrected retry after a weak password.
export function ResetForm({ token }: { token: string }): ReactNode {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setPending(true);
    setError(null);
    const result = await submitReset(token, String(form.get("new_password") ?? ""));
    setPending(false);
    if (result.ok) window.location.assign(RESET_LANDING);
    else setError(result.error);
  }

  return (
    <form onSubmit={onSubmit} className="flex w-full flex-1 flex-col gap-3">
      <p className="font-mono text-[11px] leading-relaxed text-muted-foreground">
        choose a new password - it signs you in on all your devices.
      </p>
      <Field
        id="new_password"
        name="new_password"
        type="password"
        label="new password"
        required
        autoComplete="new-password"
      />
      {error !== null && (
        <p role="alert" className="font-mono text-[10px] tracking-[0.15em] text-red-400">
          err: {error}
        </p>
      )}
      <Button
        type="submit"
        disabled={pending}
        className="mt-1 font-mono text-[11px] uppercase tracking-[0.25em]"
      >
        {pending ? "saving..." : "set new password"}
      </Button>
      <p className="font-mono text-[10px] tracking-[0.15em] text-muted-foreground/60">
        <Link href="/forgot" className="underline-offset-4 hover:text-foreground hover:underline">
          ask for a new link
        </Link>
      </p>
    </form>
  );
}
