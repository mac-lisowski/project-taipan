import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ARTIFACTS_URL,
  artifactStorage,
  deleteArtifact,
  peekArtifactSummary,
} from "./artifact-storage";

const SUMMARY = {
  id: "a1",
  title: "Report",
  type: "taipan_document",
  threadId: "t1",
  updatedAt: 1720000000,
};

function stubFetch(responder: (url: string, init?: RequestInit) => Response) {
  const fetchMock = vi.fn((url: string | URL | Request, init?: RequestInit) =>
    Promise.resolve(responder(String(url), init)),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function json(body: unknown, status = 200): Response {
  return Response.json(body, { status });
}

describe("artifactStorage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("lists with no params against the artifacts BFF route", async () => {
    const fetchMock = stubFetch(() => json({ artifacts: [], nextCursor: undefined }));

    const result = await artifactStorage.list();

    expect(fetchMock).toHaveBeenCalledWith(ARTIFACTS_URL, undefined);
    expect(result).toEqual({ artifacts: [], nextCursor: undefined });
  });

  it("sends name, repeatable type, cursor and limit as query params", async () => {
    const fetchMock = stubFetch(() => json({ artifacts: [SUMMARY], nextCursor: "c3" }));

    const result = await artifactStorage.list({
      name: "rep",
      type: ["taipan_document", "taipan_table"],
      cursor: "c2",
      limit: 25,
    });

    const url = String(fetchMock.mock.calls[0]?.[0]);
    const params = new URL(url, "http://web.test").searchParams;
    expect(url.startsWith(`${ARTIFACTS_URL}?`)).toBe(true);
    expect(params.get("name")).toBe("rep");
    expect(params.getAll("type")).toEqual(["taipan_document", "taipan_table"]);
    expect(params.get("cursor")).toBe("c2");
    expect(params.get("limit")).toBe("25");
    expect(result.nextCursor).toBe("c3");
  });

  it("passes an empty threadId through verbatim", async () => {
    const dead = { ...SUMMARY, threadId: "" };
    stubFetch(() => json({ artifacts: [dead] }));

    const { artifacts } = await artifactStorage.list();

    expect(artifacts[0]?.threadId).toBe("");
  });

  it("gets a full artifact including content", async () => {
    const artifact = { ...SUMMARY, content: { markdown: "# hi" } };
    const fetchMock = stubFetch(() => json(artifact));

    const result = await artifactStorage.get("a1");

    expect(fetchMock).toHaveBeenCalledWith(`${ARTIFACTS_URL}/a1`, undefined);
    expect(result.content).toEqual({ markdown: "# hi" });
  });

  it("remembers fetched summaries for the view's affordances", async () => {
    stubFetch(() => json({ ...SUMMARY, threadId: "", content: {} }));

    await artifactStorage.get("a1");

    expect(peekArtifactSummary("a1")?.threadId).toBe("");
  });

  it("patches content and returns the bumped summary", async () => {
    const updated = { ...SUMMARY, updatedAt: 1720000100 };
    const fetchMock = stubFetch(() => json(updated));

    const result = await artifactStorage.update({
      id: "a1",
      content: { markdown: "# edited" },
    });

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`${ARTIFACTS_URL}/a1`);
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(String(init.body))).toEqual({ content: { markdown: "# edited" } });
    expect(result).toEqual(updated);
  });

  it("throws on a non-ok response", async () => {
    stubFetch(() => new Response("nope", { status: 404 }));

    await expect(artifactStorage.get("missing")).rejects.toThrow("404");
  });
});

describe("deleteArtifact", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("DELETEs the artifact endpoint and resolves on 204", async () => {
    const fetchMock = stubFetch(() => new Response(null, { status: 204 }));

    await expect(deleteArtifact("a1")).resolves.toBeUndefined();

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`${ARTIFACTS_URL}/a1`);
    expect(init.method).toBe("DELETE");
  });

  it("throws on a non-ok response", async () => {
    stubFetch(() => new Response("nope", { status: 404 }));

    await expect(deleteArtifact("missing")).rejects.toThrow("404");
  });
});
