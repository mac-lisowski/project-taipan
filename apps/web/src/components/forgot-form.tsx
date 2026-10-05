"use client";

import Link from "next/link";
import { useState, type FormEvent, type ReactNode } from "react";
import { Button, Input, Label } from "@/ui";
import { useAuthSubmit } from "@/lib/auth-submit";

// Mock: posts to a BFF route that does not exist yet; shows a done state
// on success.
export function ForgotForm(): ReactNode {
  const [sent, setSent] = useState(false);
  const { pending, error, submit } = useAuthSubmit("/api/auth/forgot");

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const result = await submit(new FormData(e.currentTarget));
    if (result.ok) setSent(true);
  }

  if (sent) {
    return (
      <div className="flex w-full flex-1 flex-col gap-3">
        <p className="font-mono text-[11px] leading-relaxed text-muted-foreground">
          reset link sent - check your inbox.
        </p>
        <Link
          href="/"
          className="font-mono text-[10px] uppercase tracking-[0.15em] text-foreground underline-offset-4 hover:underline"
        >
          back to login
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="flex w-full flex-1 flex-col gap-3">
      <p className="font-mono text-[11px] leading-relaxed text-muted-foreground">
        enter your email - we send a reset link.
      </p>
      <div className="flex flex-col gap-1.5">
        <Label
          htmlFor="email"
          className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground"
        >
          email
        </Label>
        <Input
          id="email"
          name="email"
          type="email"
          required
          autoComplete="email"
          className="h-10 font-sans text-sm"
        />
      </div>
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
        {pending ? "sending…" : "send reset link"}
      </Button>
      <p className="font-mono text-[10px] tracking-[0.15em] text-muted-foreground/60">
        <Link href="/" className="underline-offset-4 hover:text-foreground hover:underline">
          back to login
        </Link>
      </p>
    </form>
  );
}
