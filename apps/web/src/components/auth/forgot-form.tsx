"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";
import { Field } from "@/ui";
import { AuthForm } from "@/components/auth/auth-form";

// Mock: posts to a BFF route that does not exist yet; shows a done state
// on success.
export function ForgotForm(): ReactNode {
  const [sent, setSent] = useState(false);

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
    <div className="flex w-full flex-1 flex-col gap-3">
      <p className="font-mono text-[11px] leading-relaxed text-muted-foreground">
        enter your email - we send a reset link.
      </p>
      <AuthForm
        endpoint="/api/auth/forgot"
        submitLabel="send reset link"
        pendingLabel="sending…"
        onSuccess={() => setSent(true)}
      >
        <Field
          id="email"
          name="email"
          type="email"
          label="email"
          required
          autoComplete="email"
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
