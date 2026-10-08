"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import { Button, Field } from "@/ui";
import { REGISTER_LANDING, submitActivation } from "@/lib/register";

// Sign up step two from the mailed link: upstream errors verbatim, the
// token stays fixed for a corrected retry after a weak password, and
// success assigns to the dashboard landing so the fresh session cookie
// (re-emitted by the BFF) drives the private layout.
export function ActivateForm({ token }: { token: string }): ReactNode {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setPending(true);
    setError(null);
    const result = await submitActivation(token, String(form.get("password") ?? ""));
    setPending(false);
    if (result.ok) window.location.assign(REGISTER_LANDING);
    else setError(result.error);
  }

  return (
    <form onSubmit={onSubmit} className="flex w-full flex-1 flex-col gap-3">
      <p className="font-mono text-[11px] leading-relaxed text-muted-foreground">
        choose a password - it signs you in right away.
      </p>
      <Field
        id="password"
        name="password"
        type="password"
        label="password"
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
        {pending ? "saving..." : "set password"}
      </Button>
    </form>
  );
}
