// Lazy: process.env is only populated at runtime, not during builds.
export function apiInternalUrl(): string {
  const url = process.env.API_INTERNAL_URL;
  if (!url) {
    if (process.env.NODE_ENV === "production") {
      throw new Error("API_INTERNAL_URL is required in production");
    }
    return "http://localhost:8000";
  }
  return url;
}

// Missing in production fails deploy instead of miswriting redirects.
export function publicOrigin(): string | undefined {
  const origin = process.env.PUBLIC_ORIGIN;
  if (!origin && process.env.NODE_ENV === "production") {
    throw new Error("PUBLIC_ORIGIN is required in production");
  }
  return origin;
}
