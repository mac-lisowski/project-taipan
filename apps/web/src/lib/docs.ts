import { promises as fs } from "node:fs";
import path from "node:path";

// Markdown sources live in the repo-root docs/ dir; the web app reads them
// at request time (SSG via generateStaticParams in the route).
export const DOCS_DIR =
  process.env.DOCS_DIR ?? path.resolve(process.cwd(), "..", "..", "docs");

export interface DocEntry {
  /** path segments under docs/, without the .md extension */
  slug: string[];
  title: string;
  /** display section: top dir (adr, specs, learnings) or "guides" for root files */
  section: string;
}

export interface DocGroup {
  section: string;
  entries: DocEntry[];
}

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-");
}

/** h2/h3 headings with anchor ids for the on-page TOC. */
export function extractHeadings(markdown: string): { depth: number; text: string; id: string }[] {
  return markdown
    .split("\n")
    .map((line) => line.match(/^(#{2,3})\s+(.+)$/))
    .filter((m): m is RegExpMatchArray => m !== null)
    .map((m) => ({
      depth: m[1]?.length ?? 2,
      text: (m[2] ?? "").trim(),
      id: slugify(m[2] ?? ""),
    }));
}

async function walk(dir: string, prefix: string[]): Promise<DocEntry[]> {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const out: DocEntry[] = [];
  for (const entry of entries) {
    if (entry.isDirectory()) {
      out.push(...(await walk(path.join(dir, entry.name), [...prefix, entry.name])));
    } else if (entry.name.endsWith(".md")) {
      const content = await fs.readFile(path.join(dir, entry.name), "utf8");
      const title =
        content.match(/^#\s+(.+)$/m)?.[1]?.trim() ?? entry.name.replace(/\.md$/, "");
      const slug = [...prefix, entry.name.replace(/\.md$/, "")];
      out.push({ slug, title, section: prefix[0] ?? "guides" });
    }
  }
  return out;
}

export async function listDocs(): Promise<DocEntry[]> {
  const docs = await walk(DOCS_DIR, []);
  return docs.sort((a, b) => a.slug.join("/").localeCompare(b.slug.join("/")));
}

export async function listDocGroups(): Promise<DocGroup[]> {
  const docs = await listDocs();
  const order = ["guides", "adr", "learnings", "specs"];
  const groups = new Map<string, DocEntry[]>();
  for (const doc of docs) {
    groups.set(doc.section, [...(groups.get(doc.section) ?? []), doc]);
  }
  return [...groups.entries()]
    .sort(([a], [b]) => {
      const ia = order.indexOf(a);
      const ib = order.indexOf(b);
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib) || a.localeCompare(b);
    })
    .map(([section, entries]) => ({ section, entries }));
}

export async function readDoc(slug: string[]): Promise<string | null> {
  const filePath = resolveDocPath([...slug.slice(0, -1), `${slug.at(-1)}.md`]);
  if (filePath === null) return null;
  try {
    return await fs.readFile(filePath, "utf8");
  } catch {
    return null;
  }
}

/** True when resolved stays inside DOCS_DIR; traversal must not escape. */
function contained(resolved: string): boolean {
  return resolved === DOCS_DIR || resolved.startsWith(DOCS_DIR + path.sep);
}

/** Single containment check for every docs/ read; the rule changes in one place. */
export function resolveDocPath(parts: string[]): string | null {
  const resolved = path.resolve(DOCS_DIR, ...parts);
  return contained(resolved) ? resolved : null;
}

/** Directory of a doc slug: everything before the last segment. */
function slugDir(slug: string): string {
  return slug.split("/").slice(0, -1).join("/");
}

/** Relative links resolve against the doc's own directory; escaping links pass through. */
export function docHref(slug: string, href: string): string {
  if (href.startsWith("#") || href.startsWith("http") || href.startsWith("/")) return href;
  const target = path.posix.normalize(path.posix.join(slugDir(slug), href.replace(/\.md$/, "")));
  // A link escaping the docs root keeps its original href: it 404s harmlessly.
  if (target.startsWith("..")) return href;
  return `/docs/${target}`;
}

/** Same resolution as docHref, prefixed /docs-asset/ for the asset route. */
export function assetHref(slug: string, src: string): string {
  if (src.startsWith("http") || src.startsWith("/")) return src;
  const target = path.posix.normalize(path.posix.join(slugDir(slug), src));
  return `/docs-asset/${target}`;
}
