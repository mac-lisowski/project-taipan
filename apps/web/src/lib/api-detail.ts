// One reader for upstream error bodies: prefer the API detail line,
// fall back to the status code.
export async function errorDetailOf(res: Response): Promise<string> {
  const body = (await res.json().catch(() => null)) as {
    detail?: string;
  } | null;
  return body?.detail ?? `request failed (${res.status})`;
}
