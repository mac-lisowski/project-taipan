import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { expect, test, vi } from "vitest";
import { assetHref, docHref, resolveDocPath } from "./docs";

// The verified live 404 regression: a relative link inside a docs
// section must resolve inside that section, not at the docs root.
test("docHref resolves a sibling link against the doc's directory", () => {
  expect(docHref("guides/README", "agents/README.md")).toBe(
    "/docs/guides/agents/README",
  );
});

test("docHref strips .md and ./ from relative links", () => {
  expect(docHref("adr/0001", "./0001-b.md")).toBe("/docs/adr/0001-b");
  expect(docHref("adr/0001", "b.md")).toBe("/docs/adr/b");
});

test("docHref resolves ../ upward", () => {
  expect(docHref("guides/deep/page", "../adr/0001.md")).toBe("/docs/guides/adr/0001");
});

test("docHref keeps anchors, absolute urls, and root paths untouched", () => {
  expect(docHref("adr/0001", "#section")).toBe("#section");
  expect(docHref("adr/0001", "https://example.com/x")).toBe("https://example.com/x");
  expect(docHref("adr/0001", "/guide")).toBe("/guide");
});

test("docHref leaves a root-escaping link unchanged (it 404s harmlessly)", () => {
  expect(docHref("adr/0001", "../../outside.md")).toBe("../../outside.md");
});

test("assetHref resolves relative images next to the doc", () => {
  expect(assetHref("guides/README", "img/diagram.png")).toBe(
    "/docs-asset/guides/img/diagram.png",
  );
  expect(assetHref("guides/README", "./x.png")).toBe("/docs-asset/guides/x.png");
  expect(assetHref("guides/README", "../shared/y.png")).toBe("/docs-asset/shared/y.png");
});

test("assetHref passes through external and absolute sources", () => {
  expect(assetHref("adr/0001", "https://cdn.example.com/i.png")).toBe(
    "https://cdn.example.com/i.png",
  );
  expect(assetHref("adr/0001", "/logo.png")).toBe("/logo.png");
});

test("resolveDocPath stays inside the docs root", () => {
  const inside = resolveDocPath(["guides", "README.md"]);
  expect(inside).not.toBeNull();
  expect(inside?.endsWith("guides/README.md")).toBe(true);
});

test("resolveDocPath returns null on traversal that escapes the root", () => {
  expect(resolveDocPath(["..", "..", "etc", "passwd"])).toBeNull();
});

// readDoc owns the slug -> .md filename mapping; pinning it because a
// dropped extension silently 404s every page while all gates stay green.
test("readDoc resolves a slug to its .md file and rejects traversal", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "taipan-docs-"));
  await writeFile(path.join(dir, "page.md"), "# hi");
  process.env.DOCS_DIR = dir;
  vi.resetModules();
  try {
    const { readDoc } = await import("./docs");
    expect(await readDoc(["page"])).toBe("# hi");
    expect(await readDoc(["..", "passwd"])).toBeNull();
  } finally {
    delete process.env.DOCS_DIR;
    vi.resetModules();
    await rm(dir, { recursive: true });
  }
});
