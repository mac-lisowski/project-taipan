"use client";

import { useState } from "react";
import { postJson, type ApiResult } from "./api-result";

// Alias kept here so register.ts and reset-password.ts need no edits.
export type AuthResult = ApiResult<unknown>;

// Transport and parsing live in the lib result module; this only shapes the payload.
export async function submitAuth(
  endpoint: string,
  formData: FormData,
): Promise<AuthResult> {
  return postJson(endpoint, Object.fromEntries(formData.entries()));
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
