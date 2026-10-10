// @vitest-environment happy-dom
//
// Parser tests are pure; the view tests stub the SDK's context hooks and
// heavy components so the assertions stay on our logic.

import type * as ReactHeadless from "@openuidev/react-headless";
import type * as ReactUI from "@openuidev/react-ui";
import type { ReactNode } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  nav: { path: undefined as string | undefined, navigate: vi.fn() },
  storage: null as ReactHeadless.ArtifactStorage | null,
  tableData: null as ReactUI.EditableTableProps | null,
  markdown: null as string | null,
}));

vi.mock("@openuidev/react-headless", async (importOriginal) => {
  const actual = await importOriginal<typeof ReactHeadless>();
  return { ...actual, useArtifactStorage: () => mocks.storage };
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

import { documentRenderer, tableRenderer } from "./artifact-renderers";
import { artifactStorage } from "./artifact-storage";
import type { ArtifactRendererControls } from "@openuidev/react-ui";

const ctx = { isStreaming: false };

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
  mocks.tableData = null;
  mocks.markdown = null;
});

describe("save_artifact parser: tool-call path", () => {
  const docArgs = JSON.stringify({
    title: "Q3 report",
    type: "taipan_document",
    content: "# Revenue\n\nUp.",
  });
  const tableArgs = JSON.stringify({
    title: "Staff",
    type: "taipan_table",
    content: [{ name: "Ada", role: "eng" }],
  });

  it("parses a document call into markdown props with a registered meta", () => {
    const parsed = documentRenderer.parser({ args: docArgs, response: null }, ctx);

    expect(parsed?.props).toMatchObject({
      kind: "document",
      title: "Q3 report",
      markdown: "# Revenue\n\nUp.",
    });
    expect(parsed?.meta).toMatchObject({
      version: 1,
      heading: "Q3 report",
      type: "taipan_document",
    });
    expect(parsed?.meta?.id).toMatch(/^art-[0-9a-f]+$/);
  });

  it("parses a table call into row props", () => {
    const parsed = documentRenderer.parser({ args: tableArgs, response: null }, ctx);

    // Both renderers share the tool name; whichever registers first must
    // still produce a table draft for a table call.
    expect(parsed?.props).toMatchObject({
      kind: "table",
      title: "Staff",
      rows: [{ name: "Ada", role: "eng" }],
    });
    expect(parsed?.meta?.type).toBe("taipan_table");
  });

  it("holds meta back while args are incomplete", () => {
    const partial = '{"title":"Q3 rep","type":"taipan_document","content":"# Re';
    const parsed = documentRenderer.parser(
      { args: partial, response: null },
      { isStreaming: true },
    );

    // partialJSONParse recovers the partial markdown; registration waits for
    // a complete call so the workspace entry does not flicker.
    expect(parsed?.meta).toBeNull();
  });

  it("resolves the artifact type from a partial enum string", () => {
    const partial = '{"title":"Q3 rep","type":"taipan_do';
    const parsed = documentRenderer.parser(
      { args: partial, response: null },
      { isStreaming: true },
    );

    expect(parsed?.props.kind).toBe("document");
    expect(parsed?.props.title).toBe("Q3 rep");
    expect(parsed?.meta).toBeNull();
  });

  it("keeps a stable meta id for the same call", () => {
    const first = documentRenderer.parser({ args: docArgs, response: null }, ctx);
    const second = documentRenderer.parser({ args: docArgs, response: null }, ctx);

    expect(first?.meta?.id).toBe(second?.meta?.id);
  });

  it("skips calls whose args never carry a known type", () => {
    const parsed = documentRenderer.parser(
      { args: '{"title":"x","type":"other","content":"y"}', response: null },
      ctx,
    );

    expect(parsed).toBeNull();
  });
});

describe("save_artifact parser: storage path", () => {
  it("parses stored markdown content on the document renderer", () => {
    const parsed = documentRenderer.parser(
      { args: undefined, response: { markdown: "# stored" } },
      ctx,
    );

    expect(parsed?.props).toMatchObject({ kind: "document", markdown: "# stored" });
    // Storage-opened views do not register in the thread workspace.
    expect(parsed?.meta).toBeNull();
  });

  it("parses stored rows content on the table renderer", () => {
    const parsed = tableRenderer.parser(
      { args: undefined, response: { rows: [{ a: 1 }] } },
      ctx,
    );

    expect(parsed?.props).toMatchObject({ kind: "table", rows: [{ a: 1 }] });
  });

  it("skips stored content in neither shape", () => {
    expect(
      documentRenderer.parser({ args: undefined, response: { blob: 1 } }, ctx),
    ).toBeNull();
  });
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
