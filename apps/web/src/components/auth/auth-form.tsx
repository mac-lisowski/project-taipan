"use client";

import type { FormEvent, ReactNode } from "react";
import { Button } from "@/ui";
import { useAuthSubmit } from "@/lib/auth-submit";

// Shared auth shell: owns pending state and the single error channel so
// each form supplies only its fields and success behavior.
export function AuthForm({
  endpoint,
  submitLabel,
  pendingLabel,
  onSuccess,
  children,
}: {
  endpoint: string;
  submitLabel: string;
  pendingLabel: string;
  onSuccess: () => void;
  children: ReactNode;
}): ReactNode {
  const { pending, error, submit } = useAuthSubmit(endpoint);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const result = await submit(new FormData(e.currentTarget));
    if (result.ok) onSuccess();
  }

  return (
    <form onSubmit={onSubmit} className="flex w-full flex-1 flex-col gap-3">
      {children}
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
        {pending ? pendingLabel : submitLabel}
      </Button>
    </form>
  );
}
