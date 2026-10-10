import { describe, expect, it, vi } from "vitest";

import {
  acceptFor,
  binaryPart,
  removeAttachment,
  uploadAttachment,
} from "./attachments";

const FILE_OUT = {
  id: "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  purpose: "attachment",
  scope: "tenant",
  filename: "note.png",
  content_type: "image/png",
  size_bytes: 4,
  sha256: "abc",
  created_at: "2026-01-01T00:00:00Z",
};

function stubFetch(impl: (url: string, init?: RequestInit) => Response) {
  return vi.fn((input: string | URL | Request, init?: RequestInit) =>
    Promise.resolve(impl(String(input), init)),
  ) as unknown as typeof fetch;
}

describe("acceptFor", () => {
  it("accepts images only when the model has vision", () => {
    expect(acceptFor("image/png", true)).toBe(true);
    expect(acceptFor("image/png", false)).toBe(false);
    expect(acceptFor("image/webp", false)).toBe(false);
  });

  it("accepts pdf and text regardless of vision", () => {
    expect(acceptFor("application/pdf", false)).toBe(true);
    expect(acceptFor("application/pdf", true)).toBe(true);
    expect(acceptFor("text/plain", false)).toBe(true);
  });

  it("refuses anything outside the allowlist", () => {
    expect(acceptFor("application/zip", true)).toBe(false);
    expect(acceptFor("text/html", true)).toBe(false);
    expect(acceptFor("", true)).toBe(false);
  });
});

describe("uploadAttachment", () => {
  it("posts multipart purpose/scope/file and maps the FileOut row", async () => {
    const fetchImpl = stubFetch(
      (url, init) => {
        expect(url).toBe("/api/files");
        expect(init?.method).toBe("POST");
        const form = init?.body;
        expect(form).toBeInstanceOf(FormData);
        const data = form as FormData;
        expect(data.get("purpose")).toBe("attachment");
        expect(data.get("scope")).toBe("tenant");
        const sent = data.get("file");
        expect(sent).toBeInstanceOf(File);
        expect((sent as File).name).toBe("note.png");
        return new Response(JSON.stringify(FILE_OUT), { status: 201 });
      },
    );
    const file = new File(["data"], "note.png", { type: "image/png" });
    const ref = await uploadAttachment(file, fetchImpl);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    expect(ref).toEqual({
      id: FILE_OUT.id,
      mimeType: "image/png",
      filename: "note.png",
      url: `/api/files/${FILE_OUT.id}/content`,
    });
  });

  it("throws on a non-ok response (413/415 mapped by the API)", async () => {
    const fetchImpl = stubFetch(() => new Response(null, { status: 415 }));
    const file = new File(["data"], "a.bin", { type: "image/png" });
    await expect(uploadAttachment(file, fetchImpl)).rejects.toThrow();
  });
});

describe("removeAttachment", () => {
  it("issues DELETE /api/files/{id}", async () => {
    const fetchImpl = stubFetch((url, init) => {
      expect(url).toBe(`/api/files/${FILE_OUT.id}`);
      expect(init?.method).toBe("DELETE");
      return new Response(null, { status: 204 });
    });
    await removeAttachment(FILE_OUT.id, fetchImpl);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });

  it("tolerates a 404 (the row is gone either way)", async () => {
    const fetchImpl = stubFetch(() => new Response(null, { status: 404 }));
    await expect(removeAttachment(FILE_OUT.id, fetchImpl)).resolves.toBeUndefined();
  });
});

describe("binaryPart", () => {
  it("builds the AG-UI binary part the send path emits", () => {
    expect(
      binaryPart({
        id: FILE_OUT.id,
        mimeType: "application/pdf",
        filename: "doc.pdf",
        url: `/api/files/${FILE_OUT.id}/content`,
      }),
    ).toEqual({
      type: "binary",
      mimeType: "application/pdf",
      id: FILE_OUT.id,
      filename: "doc.pdf",
      url: `/api/files/${FILE_OUT.id}/content`,
    });
  });
});

