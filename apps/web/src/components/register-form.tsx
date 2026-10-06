"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { Field } from "@/ui";
import { AuthForm } from "@/components/auth-form";

// Mock: posts to a BFF route that does not exist yet.
export function RegisterForm(): ReactNode {
  const router = useRouter();

  return (
    <div className="flex w-full flex-1 flex-col gap-3">
      <AuthForm
        endpoint="/api/auth/register"
        submitLabel="create account"
        pendingLabel="creating…"
        onSuccess={() => router.push("/")}
      >
        <div className="grid grid-cols-2 gap-3">
          <Field
            id="email"
            name="email"
            type="email"
            label="email"
            required
            autoComplete="email"
          />
          <Field
            id="name"
            name="name"
            type="text"
            label="name"
            required
            autoComplete="name"
          />
        </div>
        <Field
          id="password"
          name="password"
          type="password"
          label="password"
          required
          minLength={8}
          autoComplete="new-password"
        />
      </AuthForm>
      <p className="font-mono text-[10px] tracking-[0.15em] text-muted-foreground/60">
        <Link href="/" className="underline-offset-4 hover:text-foreground hover:underline">
          back to login
        </Link>
      </p>
    </div>
  );
}
