// @vitest-environment happy-dom
//
// The view tests stub the SDK's context hooks and heavy components so
// the assertions stay on our logic.

import type * as ReactHeadless from "@openuidev/react-headless";
import type * as ReactUI from "@openuidev/react-ui";
import type { ReactNode } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  nav: { path: undefined as string | undefined, navigate: vi.fn() },
  storage: null as ReactHeadless.ArtifactStorage | null,
  selectedThreadId: null as string | null,
  tableData: null as ReactUI.EditableTableProps | null,
  markdown: null as string | null,
}));

vi.mock("@openuidev/react-headless", async (importOriginal) => {
  const actual = await importOriginal<typeof ReactHeadless>();
  return {
    ...actual,
    useArtifactStorage: () => mocks.storage,
    useThreadList:
      <T,>(selector?: (state: { selectedThreadId: string | null }) => T) =>
        selector === undefined
          ? { selectedThreadId: mocks.selectedThreadId }
          : selector({ selectedThreadId: mocks.selectedThreadId }),
  };
});

vi.mock("@openuidev/react-ui", async (importOriginal) => {
  const actual = await importOriginal<typeof ReactUI>();
  return {
    ...actual,
    useNav: () => mocks.nav,
    EditableTable: (props: ReactUI.EditableTableProps) => {
      mocks.tableData = props;
      return <div data-testid="editable-table" />;
    },
    MarkDownRenderer: (props: ReactUI.MarkDownRendererProps) => {
      mocks.markdown = props.textMarkdown;
      return <div data-testid="markdown">{props.textMarkdown}</div>;
    },
  };
});

import { documentRenderer, tableRenderer } from "@/lib/artifact-renderers";
import { artifactStorage } from "@/lib/artifact-storage";
import type { ArtifactRendererControls } from "@openuidev/react-ui";

const SUMMARY: ReactHeadless.ArtifactSummary = {
  id: "a1",
  title: "Doc",
  type: "taipan_document",
  threadId: "t1",
  updatedAt: 1,
};

function controls(): ArtifactRendererControls {
  return {
    isActive: true,
    isStreaming: false,
    open: vi.fn(),
    close: vi.fn(),
    toggle: vi.fn(),
  };
}

function renderNode(node: ReactNode): ReturnType<typeof render> {
  return render(<>{node}</>);
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  mocks.nav.path = undefined;
  mocks.storage = null;
  mocks.selectedThreadId = null;
  mocks.tableData = null;
  mocks.markdown = null;
});

describe("artifact actual views", () => {
  const draft = {
    kind: "document" as const,
    title: "Doc",
    markdown: "# body",
    rows: [],
  };

  it("renders read-only markdown when no stored artifact id resolves", () => {
    renderNode(documentRenderer.actual(draft, controls()));

    expect(screen.getByTestId("markdown").textContent).toBe("# body");
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByLabelText(/delete/i)).toBeNull();
  });

  it("links the stored artifact to its download route", () => {
    mocks.nav.path = "artifacts/Documents/a1";
    mocks.storage = { list: vi.fn(), get: vi.fn(), update: vi.fn() };
    renderNode(documentRenderer.actual(draft, controls()));

    expect(
      screen.getByRole("link", { name: /download/i }).getAttribute("href"),
    ).toBe("/api/artifacts/a1/download");
  });

  it("resolves the stored id off-path via the thread's seen summary", async () => {
    mocks.selectedThreadId = "t1";
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(Response.json({ artifacts: [SUMMARY] }))),
    );
    await artifactStorage.list();
    renderNode(documentRenderer.actual(draft, controls()));

    const link = await screen.findByRole("link", { name: /download/i });
    expect(link.getAttribute("href")).toBe("/api/artifacts/a1/download");
  });

  it("edits markdown and saves through artifact storage update", async () => {
    mocks.nav.path = "artifacts/Documents/a1";
    const update = vi.fn(async () => SUMMARY);
    mocks.storage = { list: vi.fn(), get: vi.fn(), update };
    renderNode(documentRenderer.actual(draft, controls()));

    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "# edited" } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() =>
      expect(update).toHaveBeenCalledWith({
        id: "a1",
        content: { markdown: "# edited" },
      }),
    );
  });

  it("edits rows through the table surface and saves rows content", async () => {
    mocks.nav.path = "artifacts/Tables/a2";
    const update = vi.fn(async () => SUMMARY);
    mocks.storage = { list: vi.fn(), get: vi.fn(), update };
    const tableDraft = {
      kind: "table" as const,
      title: "T",
      markdown: "",
      rows: [{ name: "Ada" }],
    };
    renderNode(tableRenderer.actual(tableDraft, controls()));

    const props = mocks.tableData;
    expect(props).not.toBeNull();
    props?.onDataChange?.([{ id: "row-0", name: "Grace" }]);
    fireEvent.click(await screen.findByRole("button", { name: /save/i }));

    await waitFor(() =>
      expect(update).toHaveBeenCalledWith({
        id: "a2",
        content: { rows: [{ name: "Grace" }] },
      }),
    );
  });

  it("deletes after a confirm step, then closes the view", async () => {
    mocks.nav.path = "artifacts/Documents/a1";
    mocks.storage = { list: vi.fn(), get: vi.fn(), update: vi.fn() };
    const fetchMock = vi.fn(() => Promise.resolve(new Response(null, { status: 204 })));
    vi.stubGlobal("fetch", fetchMock);
    const ctl = controls();
    renderNode(documentRenderer.actual(draft, ctl));

    const del = screen.getByLabelText(/delete artifact/i);
    fireEvent.click(del);
    expect(fetchMock).not.toHaveBeenCalled();
    fireEvent.click(screen.getByLabelText(/confirm delete/i));

    await waitFor(() => expect(ctl.close).toHaveBeenCalled());
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/artifacts/a1");
    expect(init.method).toBe("DELETE");
  });

  it("hides the go-to-thread affordance for dead-thread artifacts", async () => {
    // Seed the summary cache the way the SDK's own get() would.
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          Response.json({
            id: "a9",
            title: "Dead",
            type: "taipan_document",
            threadId: "",
            updatedAt: 1,
            content: { markdown: "x" },
          }),
        ),
      ),
    );
    await artifactStorage.get("a9");
    mocks.nav.path = "artifacts/Documents/a9";
    mocks.storage = { list: vi.fn(), get: vi.fn(), update: vi.fn() };

    renderNode(documentRenderer.actual(draft, controls()));

    const style = document.querySelector("style");
    expect(style?.textContent).toContain("Go to thread");
  });
});
