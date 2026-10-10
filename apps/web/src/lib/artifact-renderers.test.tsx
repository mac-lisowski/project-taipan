// @vitest-environment happy-dom
//
// Parser tests are pure; the view tests live in
// components/chat/artifact-views.test.tsx beside the component.

import { describe, expect, it } from "vitest";

import { documentRenderer, tableRenderer } from "./artifact-renderers";

const ctx = { isStreaming: false };

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
