"use client";

import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { Field } from "@/ui";
import { AuthForm } from "@/components/auth/auth-form";

// First-run setup: posts email plus password to /api/setup, which sets
// the session cookie, then lands straight on chat.
export function SetupForm(): ReactNode {
  const router = useRouter();

  return (
    <div className="flex w-full flex-1 flex-col gap-3">
      <div className="flex flex-col gap-1">
        <p className="font-mono text-[10px] tracking-[0.35em] text-signal">
          first-run installation
        </p>
        <p className="font-mono text-[11px] text-foreground">
          No users exist yet. Create the admin account to set up this instance.
        </p>
      </div>
      <AuthForm
        endpoint="/api/setup"
        submitLabel="set up"
        pendingLabel="setting up…"
        onSuccess={() => router.push("/chat")}
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
            id="password"
            name="password"
            type="password"
            label="password"
            required
            minLength={8}
            autoComplete="new-password"
          />
        </div>
      </AuthForm>
    </div>
  );
}
