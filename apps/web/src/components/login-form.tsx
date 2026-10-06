"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { Field } from "@/ui";
import { AuthForm } from "@/components/auth-form";

// Posts to the BFF catch-all at /api/auth/login; the upstream session
// cookie is re-emitted by the proxy. Shows the upstream error verbatim.
export function LoginForm(): ReactNode {
  return (
    <div className="flex w-full flex-1 flex-col gap-3">
      <AuthForm
        endpoint="/api/auth/login"
        submitLabel="enter"
        pendingLabel="checking…"
        onSuccess={() => window.location.reload()}
      >
        <div className="grid grid-cols-2 gap-3">
          <Field
            id="email"
            name="email"
            type="email"
            label="email"
            required
            autoComplete="username"
          />
          <Field
            id="password"
            name="password"
            type="password"
            label="password"
            required
            autoComplete="current-password"
          />
        </div>
      </AuthForm>
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
    </div>
  );
}
