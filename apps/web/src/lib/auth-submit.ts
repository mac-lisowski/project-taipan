"use client";

import { useState } from "react";

export type AuthResult = { ok: true } | { ok: false; error: string };

// One submit path for every auth form: FormData -> JSON POST to the BFF,
// upstream `detail` surfaced verbatim, network errors folded into the same
// error channel so no form leaks an unhandled rejection.
export async function submitAuth(
  endpoint: string,
  formData: FormData,
): Promise<AuthResult> {
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.fromEntries(formData.entries())),
    });
    if (res.ok) return { ok: true };
    const data = (await res.json().catch(() => null)) as {
      detail?: string;
    } | null;
    return { ok: false, error: data?.detail ?? `request failed (${res.status})` };
  } catch {
    return { ok: false, error: "network error" };
  }
}

export function useAuthSubmit(endpoint: string): {
  pending: boolean;
  error: string | null;
  submit: (formData: FormData) => Promise<AuthResult>;
} {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (formData: FormData): Promise<AuthResult> => {
    setPending(true);
    setError(null);
    try {
      const result = await submitAuth(endpoint, formData);
      if (!result.ok) setError(result.error);
      return result;
    } finally {
      setPending(false);
    }
  };

  return { pending, error, submit };
}
