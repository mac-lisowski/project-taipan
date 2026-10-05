"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { FormEvent, ReactNode } from "react";
import { Button, Input, Label } from "@/ui";
import { useAuthSubmit } from "@/lib/auth-submit";

// Mock: posts to a BFF route that does not exist yet.
export function RegisterForm(): ReactNode {
  const router = useRouter();
  const { pending, error, submit } = useAuthSubmit("/api/auth/register");

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const result = await submit(new FormData(e.currentTarget));
    if (result.ok) router.push("/");
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
            autoComplete="email"
            className="h-10 font-sans text-sm"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="name" className={labelCls}>
            name
          </Label>
          <Input
            id="name"
            name="name"
            type="text"
            required
            autoComplete="name"
            className="h-10 font-sans text-sm"
          />
        </div>
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
          minLength={8}
          autoComplete="new-password"
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
        {pending ? "creating…" : "create account"}
      </Button>
      <p className="font-mono text-[10px] tracking-[0.15em] text-muted-foreground/60">
        <Link href="/" className="underline-offset-4 hover:text-foreground hover:underline">
          back to login
        </Link>
      </p>
    </form>
  );
}
