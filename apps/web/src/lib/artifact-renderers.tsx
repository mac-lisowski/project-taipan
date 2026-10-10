import {
  defineArtifactCategories,
  defineArtifactRenderer,
  partialJSONParse,
  type ArtifactRendererControls,
  type ParsedArtifact,
} from "@openuidev/react-headless";
import { FileText, Table2 } from "lucide-react";

import {
  ArtifactActual,
  ArtifactPreview,
} from "@/components/chat/artifact-views";

// Mirrors api/chat/tools.py SAVE_ARTIFACT_TOOL.
export const SAVE_ARTIFACT_TOOL = "save_artifact";
export const DOCUMENT_TYPE = "taipan_document";
export const TABLE_TYPE = "taipan_table";

export type ArtifactRow = Record<string, unknown>;

// One props type for both renderers: only the first-registered renderer
// sees a `save_artifact` call (first toolName registration wins), so every
// parser must produce whichever draft the call carries.
export type ArtifactDraft = {
  kind: "document" | "table";
  title: string;
  markdown: string;
  rows: ArtifactRow[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

// Mid-stream the enum arrives character by character ("taipan_do"); a
// unique prefix match still resolves the kind for the live preview.
function resolveKind(type: unknown): ArtifactDraft["kind"] | null {
  if (type === DOCUMENT_TYPE) return "document";
  if (type === TABLE_TYPE) return "table";
  if (typeof type !== "string" || type === "") return null;
  const candidates: ArtifactDraft["kind"][] = [];
  if (DOCUMENT_TYPE.startsWith(type)) candidates.push("document");
  if (TABLE_TYPE.startsWith(type)) candidates.push("table");
  return candidates.length === 1 ? (candidates[0] ?? null) : null;
}

function normalizeRows(value: unknown): ArtifactRow[] {
  if (!Array.isArray(value)) return [];
  return value.map((row) => (isRecord(row) ? row : { value: row }));
}

// Stable per call: the tool-call id never reaches the parser, so the id is
// derived from title+kind. Only computed on closed args, so it never moves.
function stableId(title: string, kind: string): string {
  const input = `${kind}:${title}`;
  let hash = 0x811c9dc5;
  for (let i = 0; i < input.length; i += 1) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return `art-${(hash >>> 0).toString(16)}`;
}

const META_TYPE: Record<ArtifactDraft["kind"], string> = {
  document: DOCUMENT_TYPE,
  table: TABLE_TYPE,
};

// Live path: args is a possibly-partial JSON string, response always null
// (no tool result is ever emitted, so isStreaming never clears). Meta must
// wait for closed args - strict JSON.parse - or meta.id keeps moving.
function parseCallArgs(argsJson: string): ParsedArtifact<ArtifactDraft> | null {
  const loose = partialJSONParse(argsJson);
  if (!isRecord(loose)) return null;
  const kind = resolveKind(loose.type);
  if (kind === null) return null;
  const title = typeof loose.title === "string" ? loose.title : "";
  const draft: ArtifactDraft =
    kind === "document"
      ? {
          kind,
          title,
          markdown: typeof loose.content === "string" ? loose.content : "",
          rows: [],
        }
      : {
          kind,
          title,
          markdown: "",
          rows: normalizeRows(loose.content),
        };
  let closed: unknown = null;
  try {
    closed = JSON.parse(argsJson);
  } catch {
    // Args still streaming: render the partial draft, register nothing yet.
  }
  if (!isRecord(closed)) return { props: draft, meta: null };
  const complete =
    typeof closed.title === "string" &&
    closed.title !== "" &&
    (kind === "document"
      ? typeof closed.content === "string"
      : Array.isArray(closed.content));
  if (!complete) return { props: draft, meta: null };
  return {
    props: draft,
    meta: {
      id: stableId(title, kind),
      version: 1,
      heading: title,
      type: META_TYPE[kind],
    },
  };
}

// Storage path: response is the stored content; meta stays null because
// browser-opened artifacts never join the thread workspace registry.
function parseStored(content: unknown): ParsedArtifact<ArtifactDraft> | null {
  if (!isRecord(content)) return null;
  if (typeof content.markdown === "string") {
    return {
      props: { kind: "document", title: "", markdown: content.markdown, rows: [] },
      meta: null,
    };
  }
  if (Array.isArray(content.rows)) {
    return {
      props: { kind: "table", title: "", markdown: "", rows: normalizeRows(content.rows) },
      meta: null,
    };
  }
  return null;
}

function parseSaveArtifact(raw: {
  args: unknown;
  response: unknown;
}): ParsedArtifact<ArtifactDraft> | null {
  if (raw.response !== null && raw.response !== undefined) {
    return parseStored(raw.response);
  }
  if (typeof raw.args !== "string") return null;
  return parseCallArgs(raw.args);
}

const shared = {
  toolName: SAVE_ARTIFACT_TOOL,
  parser: parseSaveArtifact,
  preview: (props: ArtifactDraft, controls: ArtifactRendererControls) => (
    <ArtifactPreview draft={props} controls={controls} />
  ),
  actual: (props: ArtifactDraft, controls: ArtifactRendererControls) => (
    <ArtifactActual draft={props} controls={controls} />
  ),
};

export const documentRenderer = defineArtifactRenderer<ArtifactDraft>({
  type: DOCUMENT_TYPE,
  label: "Document",
  icon: <FileText size="1em" />,
  ...shared,
});

export const tableRenderer = defineArtifactRenderer<ArtifactDraft>({
  type: TABLE_TYPE,
  label: "Table",
  icon: <Table2 size="1em" />,
  ...shared,
});

// Spread onto <AgentInterface>: gives both artifactRenderers and
// artifactCategories from one declaration per category.
export const artifactSurface = defineArtifactCategories([
  {
    name: "Documents",
    renderers: [documentRenderer],
    icon: <FileText size="1em" />,
  },
  {
    name: "Tables",
    renderers: [tableRenderer],
    icon: <Table2 size="1em" />,
  },
]);
