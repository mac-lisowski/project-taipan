// Trusted browser-facing origin resolution. Client-supplied
// x-forwarded-* headers are not trusted.
export function resolveTrustedOrigin(
  req: Request,
  explicitOrigin?: string,
): string {
  if (explicitOrigin) return explicitOrigin;
  const host = req.headers.get("host") ?? "localhost";
  const proto = new URL(req.url).protocol.replace(":", "");
  return `${proto || "http"}://${host}`;
}
