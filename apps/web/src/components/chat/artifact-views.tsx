"use client";

import { useArtifactStorage, useThreadList } from "@openuidev/react-headless";
import {
  EditableTable,
  IconButton,
  MarkDownRenderer,
  useNav,
  type ArtifactRendererControls,
  type EditableTableColumn,
  type EditableTableRow,
} from "@openuidev/react-ui";
import { Check, Download, FileText, Table2, Trash2 } from "lucide-react";
import { useState, type ReactNode } from "react";

import {
  artifactDownloadUrl,
  deleteArtifact,
  findArtifactSummary,
  peekArtifactSummary,
} from "@/lib/artifact-storage";
import {
  DOCUMENT_TYPE,
  TABLE_TYPE,
  type ArtifactDraft,
  type ArtifactRow,
} from "@/lib/artifact-renderers";

const ARTIFACTS_PREFIX = "artifacts/";

// The reserved browser path is artifacts/{category}/{id}; anywhere else is
// the in-thread detailed view, where no stored id exists to PATCH.
function artifactIdFromPath(path: string | undefined): string | null {
  if (path === undefined || !path.startsWith(ARTIFACTS_PREFIX)) return null;
  const segments = path.slice(ARTIFACTS_PREFIX.length).split("/");
  const encoded = segments.length === 2 ? segments[1] : undefined;
  return encoded === undefined || encoded === "" ? null : decodeURIComponent(encoded);
}

// SDK 0.17.0 renders "Go to thread" unconditionally even when threadId is
// ""; the click would selectThread("") and 404 the thread load. Hide it
// until the SDK gates the affordance itself.
const DEAD_THREAD_CSS =
  ".openui-agent-artifact-view__header > :last-child, [aria-label='Go to thread'] { display: none !important; }";

export function ArtifactPreview({
  draft,
  controls,
}: {
  draft: ArtifactDraft;
  controls: ArtifactRendererControls;
}): ReactNode {
  const Icon = draft.kind === "table" ? Table2 : FileText;
  const detail =
    draft.kind === "table"
      ? `${draft.rows.length} ${draft.rows.length === 1 ? "row" : "rows"}`
      : "Document";
  return (
    <button
      type="button"
      onClick={controls.open}
      aria-label={`open ${draft.title || "artifact"}`}
      className="my-2 flex w-full items-center gap-3 rounded-lg border border-border bg-card px-3 py-2.5 text-left text-sm transition-colors hover:bg-accent"
    >
      <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
      <span className="min-w-0 flex-1 truncate font-medium">
        {draft.title || "Untitled artifact"}
      </span>
      <span className="shrink-0 text-xs text-muted-foreground">{detail}</span>
    </button>
  );
}

export function ArtifactActual({
  draft,
  controls,
}: {
  draft: ArtifactDraft;
  controls: ArtifactRendererControls;
}): ReactNode {
  const { path } = useNav();
  const storage = useArtifactStorage();
  const selectedThreadId = useThreadList((state) => state.selectedThreadId);
  const artifactId = artifactIdFromPath(path);
  const editable = artifactId !== null && storage !== null;
  const summary = artifactId === null ? undefined : peekArtifactSummary(artifactId);
  // The canonical path carries the id; in the in-thread detailed view the
  // stored id only resolves when the summary was listed at least once.
  const storedId =
    artifactId ??
    (selectedThreadId === null
      ? null
      : (findArtifactSummary({
          threadId: selectedThreadId,
          title: draft.title,
          type: draft.kind === "table" ? TABLE_TYPE : DOCUMENT_TYPE,
        })?.id ?? null));
  const [markdown, setMarkdown] = useState(draft.markdown);
  const [rows, setRows] = useState<ArtifactRow[]>(draft.rows);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirming, setConfirming] = useState(false);

  async function save(): Promise<void> {
    if (artifactId === null || storage === null) return;
    setSaving(true);
    try {
      await storage.update({
        id: artifactId,
        content: draft.kind === "document" ? { markdown } : { rows },
      });
      setDirty(false);
    } finally {
      setSaving(false);
    }
  }

  // Two-tap confirm keeps the affordance inside the view; no window.confirm.
  async function remove(): Promise<void> {
    if (artifactId === null) return;
    await deleteArtifact(artifactId);
    controls.close();
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {summary?.threadId === "" && <style>{DEAD_THREAD_CSS}</style>}
      {(editable || storedId !== null) && (
        <div className="flex items-center justify-end gap-1.5 border-b border-border px-3 py-2">
          {storedId !== null && (
            <a
              href={artifactDownloadUrl(storedId)}
              download
              aria-label="download artifact"
              className="rounded-md border border-border px-3 py-1 text-xs font-medium transition-colors hover:bg-accent"
            >
              <Download size="1em" className="inline" /> Download
            </a>
          )}
          {editable && (
            <>
              <button
                type="button"
                onClick={() => void save()}
                disabled={!dirty || saving}
                className="rounded-md border border-border px-3 py-1 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50"
              >
                {saving ? "Saving…" : "Save"}
              </button>
              {confirming ? (
                <IconButton
                  variant="tertiary"
                  size="small"
                  icon={<Check size="1em" />}
                  aria-label="confirm delete"
                  onClick={() => void remove()}
                />
              ) : (
                <IconButton
                  variant="tertiary"
                  size="small"
                  icon={<Trash2 size="1em" />}
                  aria-label="delete artifact"
                  onClick={() => setConfirming(true)}
                />
              )}
            </>
          )}
        </div>
      )}
      <div className="min-h-0 flex-1 overflow-auto p-3">
        {draft.kind === "document" ? (
          editable ? (
            <textarea
              value={markdown}
              onChange={(event) => {
                setMarkdown(event.target.value);
                setDirty(true);
              }}
              className="h-full w-full resize-none bg-transparent font-mono text-sm outline-none"
            />
          ) : (
            <MarkDownRenderer textMarkdown={draft.markdown} />
          )
        ) : editable ? (
          <ArtifactTableEditor
            rows={rows}
            onChange={(next) => {
              setRows(next);
              setDirty(true);
            }}
          />
        ) : (
          <ArtifactTableStatic rows={draft.rows} />
        )}
      </div>
    </div>
  );
}

function rowKeys(rows: ArtifactRow[]): string[] {
  const keys: string[] = [];
  for (const row of rows) {
    for (const key of Object.keys(row)) {
      if (!keys.includes(key)) keys.push(key);
    }
  }
  return keys;
}

// EditableTable rows need an `id` key; a user column named `id` is moved to
// `__id` so the synthetic key never clobbers data, and restored on save.
function toTableData(rows: ArtifactRow[]): EditableTableRow[] {
  return rows.map((row, index) => {
    const { id: own, ...rest } = row;
    const data: EditableTableRow = { ...rest, id: `row-${index}` };
    if (own !== undefined) data.__id = own;
    return data;
  });
}

function fromTableData(data: EditableTableRow[]): ArtifactRow[] {
  return data.map((row) => {
    const copy: Record<string, unknown> = { ...row };
    delete copy.id;
    const own = copy.__id;
    delete copy.__id;
    return own === undefined ? copy : { ...copy, id: own };
  });
}

function tableColumns(rows: ArtifactRow[]): EditableTableColumn[] {
  return rowKeys(rows).map((key) =>
    key === "id" ? { key: "__id", header: "id" } : { key, header: key },
  );
}

function ArtifactTableEditor({
  rows,
  onChange,
}: {
  rows: ArtifactRow[];
  onChange: (rows: ArtifactRow[]) => void;
}): ReactNode {
  return (
    <EditableTable
      data={toTableData(rows)}
      columns={tableColumns(rows)}
      onDataChange={(data) => onChange(fromTableData(data))}
    />
  );
}

function cellText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

// Read-only table for the in-thread detailed view, where there is no
// stored artifact id to save against.
function ArtifactTableStatic({ rows }: { rows: ArtifactRow[] }): ReactNode {
  const columns = rowKeys(rows);
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr>
          {columns.map((key) => (
            <th
              key={key}
              className="border-b border-border px-2 py-1.5 text-left font-medium"
            >
              {key}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr key={index}>
            {columns.map((key) => (
              <td key={key} className="border-b border-border/50 px-2 py-1.5">
                {cellText(row[key])}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
