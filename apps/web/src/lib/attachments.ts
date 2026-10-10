// Composer file attachments: immediate upload on pick through the BFF
// files API, draft chips, and the AG-UI parts the send path emits.

export const MAX_ATTACHMENTS = 5;
export const ATTACH_ACCEPT = "image/*,application/pdf,text/plain";

// The uploaded file row, reduced to what a chip and a binary part need.
export type AttachmentRef = {
  id: string;
  mimeType: string;
  filename: string;
  url: string;
};

// A composer chip: uploading until the files API answers, failed when it
// rejects. `id`/`url` stay null until the row exists.
export type AttachmentDraft = {
  key: string;
  status: "uploading" | "ready" | "failed";
  id: string | null;
  mimeType: string;
  filename: string;
  url: string | null;
};

// AG-UI InputContent subset the composer sends; assignable to the SDK's
// InputContent union (text and binary members).
export type TextPart = { type: "text"; text: string };
export type BinaryPart = {
  type: "binary";
  mimeType: string;
  id?: string;
  url?: string;
  filename?: string;
};
export type MessagePart = TextPart | BinaryPart;

export class AttachmentUploadError extends Error {
  constructor(public readonly status: number) {
    super(`attachment upload answered ${status}`);
  }
}

// Vision gate: images need a vision-capable model; pdf and text always
// attach because the API resolves them to text when the model cannot.
export function acceptFor(mime: string, vision: boolean): boolean {
  if (mime.startsWith("image/")) return vision;
  return mime === "application/pdf" || mime === "text/plain";
}

export function binaryPart(ref: AttachmentRef): BinaryPart {
  return {
    type: "binary",
    mimeType: ref.mimeType,
    id: ref.id,
    filename: ref.filename,
    url: ref.url,
  };
}

// POST /api/files multipart; the session cookie rides the BFF. The API
// enforces the allowlist and the 10 MiB cap (413/415 on violation).
export async function uploadAttachment(
  file: File,
  fetchImpl: typeof fetch = fetch,
): Promise<AttachmentRef> {
  const form = new FormData();
  form.set("purpose", "attachment");
  form.set("scope", "tenant");
  form.set("file", file);
  const res = await fetchImpl("/api/files", { method: "POST", body: form });
  if (!res.ok) throw new AttachmentUploadError(res.status);
  const row = (await res.json()) as {
    id: string;
    filename: string;
    content_type: string;
  };
  return {
    id: row.id,
    mimeType: row.content_type,
    filename: row.filename,
    url: `/api/files/${row.id}/content`,
  };
}

// 204 on delete; a 404 means the row is already gone, same end state.
export async function removeAttachment(
  id: string,
  fetchImpl: typeof fetch = fetch,
): Promise<void> {
  const res = await fetchImpl(`/api/files/${id}`, { method: "DELETE" });
  if (!res.ok && res.status !== 404) {
    throw new AttachmentUploadError(res.status);
  }
}
