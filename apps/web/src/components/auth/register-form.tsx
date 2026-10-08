"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import { Button, Field } from "@/ui";
import { submitRegister } from "@/lib/register";

// Sign up step one: email only. The API answers the same for every
// address, so success always swaps the form for the mailed-link note.
export function RegisterForm(): ReactNode {
  const [pending, setPending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setPending(true);
    setError(null);
    const result = await submitRegister(String(form.get("email") ?? ""));
    setPending(false);
    if (result.ok) setSent(true);
    else setError(result.error);
  }

  if (sent) {
    return (
      <p role="status" className="font-mono text-[11px] leading-relaxed text-muted-foreground">
        mail is on the way - open the link inside to set your password.
      </p>
    );
  }

  return (
    <form onSubmit={onSubmit} className="flex w-full flex-1 flex-col gap-3">
      <Field
        id="email"
        name="email"
        type="email"
        label="email"
        required
        autoComplete="username"
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
        {pending ? "sending..." : "sign up"}
      </Button>
    </form>
  );
}
