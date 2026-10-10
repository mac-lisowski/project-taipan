import type {
  Artifact,
  ArtifactListParams,
  ArtifactStorage,
  ArtifactSummary,
} from "@openuidev/react-headless";

// Browser-facing BFF route only; the catch-all relays it to the API.
export const ARTIFACTS_URL = "/api/artifacts";

// The SDK artifact view fetches via get() and then hands only `content`
// to the renderer's parser, so the view cannot see `threadId`. The last
// seen summaries live here for view-level affordances (dead-thread).
const seen = new Map<string, ArtifactSummary>();
// FIFO cap so a long session cannot grow the map without bound.
const SEEN_MAX = 500;

export function peekArtifactSummary(id: string): ArtifactSummary | undefined {
  return seen.get(id);
}

// Off-path views link a draft to its stored row via the seen summaries;
// duplicates get a content check so the download never resolves wrong.
export async function resolveArtifactId(match: {
  threadId: string;
  title: string;
  type: string;
  content: unknown;
}): Promise<string | undefined> {
  const candidates = [...seen.values()].filter(
    (summary) =>
      summary.threadId === match.threadId &&
      summary.title === match.title &&
      summary.type === match.type,
  );
  if (candidates.length === 0) return undefined;
  if (candidates.length === 1) return candidates[0]?.id;
  const wanted = JSON.stringify(match.content);
  for (const candidate of candidates) {
    try {
      const artifact = await artifactStorage.get(candidate.id);
      if (JSON.stringify(artifact.content) === wanted) return candidate.id;
    } catch {
      // A failed fetch only skips that candidate.
    }
  }
  return undefined;
}

// Anchors hit the BFF route directly; the api streams an attachment.
export function artifactDownloadUrl(id: string): string {
  return `${ARTIFACTS_URL}/${encodeURIComponent(id)}/download`;
}

function remember(summary: ArtifactSummary): void {
  if (seen.size >= SEEN_MAX) {
    const oldest = seen.keys().next().value;
    if (oldest !== undefined) seen.delete(oldest);
  }
  seen.set(summary.id, summary);
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(path, init);
  if (!res.ok) {
    throw new Error(
      `artifactStorage: ${init?.method ?? "GET"} ${path} failed: ${res.status} ${res.statusText}`,
    );
  }
  return res;
}

// Hand-written ArtifactStorage over /api/artifacts; the SDK's restStorage
// covers only threads. Wire keys are already camelCase.
export const artifactStorage: ArtifactStorage = {
  async list(params: ArtifactListParams = {}) {
    const query = new URLSearchParams();
    if (params.name !== undefined && params.name !== "") {
      query.set("name", params.name);
    }
    for (const type of params.type ?? []) {
      query.append("type", type);
    }
    if (params.cursor !== undefined && params.cursor !== "") {
      query.set("cursor", params.cursor);
    }
    if (params.limit !== undefined) {
      query.set("limit", String(params.limit));
    }
    const suffix = query.size > 0 ? `?${query.toString()}` : "";
    const res = await request(`${ARTIFACTS_URL}${suffix}`);
    const body = (await res.json()) as {
      artifacts: ArtifactSummary[];
      nextCursor?: string;
    };
    body.artifacts.forEach(remember);
    return body;
  },

  async get(id: string): Promise<Artifact> {
    const res = await request(`${ARTIFACTS_URL}/${encodeURIComponent(id)}`);
    const artifact = (await res.json()) as Artifact;
    remember(artifact);
    return artifact;
  },

  async update(patch: { id: string; content: unknown }): Promise<ArtifactSummary> {
    const res = await request(`${ARTIFACTS_URL}/${encodeURIComponent(patch.id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: patch.content }),
    });
    const summary = (await res.json()) as ArtifactSummary;
    remember(summary);
    return summary;
  },
};

// The SDK ArtifactStorage contract has no delete; the workspace button
// calls the endpoint directly.
export async function deleteArtifact(id: string): Promise<void> {
  await request(`${ARTIFACTS_URL}/${encodeURIComponent(id)}`, { method: "DELETE" });
  seen.delete(id);
}
