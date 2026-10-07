"use client";

import { useState } from "react";
import type { ChangeEvent, FormEvent, ReactNode } from "react";
import { Button, Field, cn } from "@/ui";
import { PASSWORD_RULES, changePassword, outcomeNote, ruleMet } from "@/lib/password-change";

// Account page change form: rules up front, double-entry check before any
// request, upstream errors verbatim, success note carries the other-device
// outcome so the user knows this device stays signed in.
export function ChangePasswordForm(): ReactNode {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [next, setNext] = useState("");

  function onNextChange(e: ChangeEvent<HTMLInputElement>) {
    setNext(e.target.value);
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setPending(true);
    setError(null);
    setNote(null);
    const result = await changePassword(form);
    setPending(false);
    if (result.ok) setNote(outcomeNote(result.otherDevicesSignedOut));
    else setError(result.error);
  }

  return (
    <form onSubmit={onSubmit} className="flex w-full flex-1 flex-col gap-3">
      <p className="font-mono text-[10px] tracking-[0.15em] text-muted-foreground">
        rules: {PASSWORD_RULES}
      </p>
      <Field
        id="current_password"
        name="current_password"
        type="password"
        label="current password"
        required
        autoComplete="current-password"
      />
      <Field
        id="new_password"
        name="new_password"
        type="password"
        label="new password"
        required
        autoComplete="new-password"
        value={next}
        onChange={onNextChange}
      />
      <div
        aria-hidden
        className="h-0.5 w-full overflow-hidden rounded bg-border"
        data-testid="strength-bar"
      >
        <div
          className={cn(
            "h-full transition-all",
            ruleMet(next) ? "w-full bg-emerald-400" : "w-1/3 bg-red-400",
          )}
        />
      </div>
      <Field
        id="confirm_new_password"
        name="confirm_new_password"
        type="password"
        label="repeat new"
        required
        autoComplete="new-password"
      />
      {error !== null && (
        <p role="alert" className="font-mono text-[10px] tracking-[0.15em] text-red-400">
          err: {error}
        </p>
      )}
      {note !== null && (
        <p role="status" className="font-mono text-[10px] tracking-[0.15em] text-emerald-400">
          {note}
        </p>
      )}
      <Button
        type="submit"
        disabled={pending}
        className="mt-1 font-mono text-[11px] uppercase tracking-[0.25em]"
      >
        {pending ? "changing…" : "change password"}
      </Button>
    </form>
  );
}
