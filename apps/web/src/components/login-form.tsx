"use client";

import Link from "next/link";
import type { FormEvent, ReactNode } from "react";
import { Button, Input, Label } from "@/ui";
import { useAuthSubmit } from "@/lib/auth-submit";

// Posts to the BFF catch-all at /api/auth/login; the upstream session
// cookie is re-emitted by the proxy. Shows the upstream error verbatim.
export function LoginForm(): ReactNode {
  const { pending, error, submit } = useAuthSubmit("/api/auth/login");

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const result = await submit(new FormData(e.currentTarget));
    if (result.ok) window.location.reload();
  }

  const labelCls =
    "font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground";

  return (
    <form onSubmit={onSubmit} className="flex w-full flex-1 flex-col gap-3">
      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="email" className={labelCls}>
            email
          </Label>
          <Input
            id="email"
            name="email"
            type="email"
            required
            autoComplete="username"
            className="h-10 font-sans text-sm"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="password" className={labelCls}>
            password
          </Label>
          <Input
            id="password"
            name="password"
            type="password"
            required
            autoComplete="current-password"
            className="h-10 font-sans text-sm"
          />
        </div>
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
        {pending ? "checking…" : "enter"}
      </Button>
      <div className="flex items-center justify-between font-mono text-[10px] tracking-[0.15em]">
        <Link
          href="/register"
          className="text-muted-foreground underline-offset-4 transition-colors hover:text-foreground hover:underline"
        >
          register
        </Link>
        <Link
          href="/forgot"
          className="text-muted-foreground underline-offset-4 transition-colors hover:text-foreground hover:underline"
        >
          forgot?
        </Link>
      </div>
    </form>
  );
}
