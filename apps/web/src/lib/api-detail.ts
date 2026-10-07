// Prefer the API detail line from an upstream error body; else the status.
export async function errorDetailOf(res: Response): Promise<string> {
  const body = (await res.json().catch(() => null)) as {
    detail?: string;
  } | null;
  return body?.detail ?? `request failed (${res.status})`;
}
