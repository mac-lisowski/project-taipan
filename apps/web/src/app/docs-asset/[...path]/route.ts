import { promises as fs } from "node:fs";
import path from "node:path";
import { resolveDocPath } from "@/lib/docs";

const TYPES: Record<string, string> = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
};

// Serves binary assets referenced from markdown docs (images etc).
// Path is resolved inside docs/ - anything escaping it 404s.
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  const { path: parts } = await params;
  const filePath = resolveDocPath(parts);
  const ext = path.extname(filePath ?? "").toLowerCase();
  if (filePath === null || !(ext in TYPES)) {
    return new Response("not found", { status: 404 });
  }
  try {
    const data = await fs.readFile(filePath);
    return new Response(new Uint8Array(data), {
      headers: { "Content-Type": TYPES[ext] ?? "application/octet-stream" },
    });
  } catch {
    return new Response("not found", { status: 404 });
  }
}
