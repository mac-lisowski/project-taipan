// @vitest-environment happy-dom
//
// DOM tests for the custom composer: attachment pick/upload/remove and
// the parts-array send shape. The SDK thread hook is stubbed; the model
// and queue stores are real instances built with stubbed fetch impls.

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChatComposer } from "@/components/chat/chat-composer";
import { removeAttachment, uploadAttachment } from "@/lib/attachments";
import { ChatModelProvider } from "@/lib/chat-model-context";
import { createChatModelStore, type ChatModel } from "@/lib/chat-model";
import { ChatQueueProvider } from "@/lib/chat-queue-context";
import { createChatQueueStore, type ChatQueueStore } from "@/lib/chat-queue";

const THREAD = "11111111-1111-1111-1111-111111111111";
const FILE_ID = "f47ac10b-58cc-4372-a567-0e02b2c3d479";

vi.mock("@openuidev/react-headless", () => ({
  useThread: (selector: (s: unknown) => unknown) => selector(threadState),
}));

vi.mock("@/lib/attachments", async (importOriginal) => ({
  ...((await importOriginal()) as object),
  uploadAttachment: vi.fn(),
  removeAttachment: vi.fn(),
}));

const uploadMock = vi.mocked(uploadAttachment);
const removeMock = vi.mocked(removeAttachment);

// Mutable SDK thread state; each test resets it.
const threadState = {
  processMessage: vi.fn<(m: unknown) => Promise<void>>(),
  cancelMessage: vi.fn(),
  isRunning: false,
  isLoadingMessages: false,
  messages: [] as { role: string; content: unknown }[],
};

function modelsJson(models: ChatModel[]): Response {
  return new Response(JSON.stringify(models), {
    headers: { "content-type": "application/json" },
  });
}

// The model store only loads over fetch; other calls are irrelevant here.
async function makeModelStore(models: ChatModel[]) {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.resolve(modelsJson(models))),
  );
  const store = createChatModelStore();
  await store.load();
  return store;
}

function makeQueueStore(postBodies: string[]): ChatQueueStore {
  const fetchImpl = (async (_url: string, init?: RequestInit) => {
    if (init?.method === "POST") {
      postBodies.push(typeof init.body === "string" ? init.body : "");
      return new Response(
        JSON.stringify({
          id: "q1",
          threadId: THREAD,
          seq: 1,
          content: JSON.parse(typeof init.body === "string" ? init.body : "{}").content,
          createdAt: 1,
        }),
        { headers: { "content-type": "application/json" } },
      );
    }
    return new Response(JSON.stringify([]), {
      headers: { "content-type": "application/json" },
    });
  }) as typeof fetch;
  return createChatQueueStore(fetchImpl);
}

async function renderComposer(opts: {
  models?: ChatModel[];
  queue?: ChatQueueStore;
} = {}) {
  const modelStore = await makeModelStore(
    opts.models ?? [
      { id: "m-vision", name: "Vision", default: true, vision: true },
    ],
  );
  const queue = opts.queue ?? createChatQueueStore(async () => new Response("[]"));
  await queue.hydrate(THREAD);
  return render(
    <ChatQueueProvider store={queue}>
      <ChatModelProvider store={modelStore}>
        <ChatComposer starters={[]} />
      </ChatModelProvider>
    </ChatQueueProvider>,
  );
}

function fileInput(container: HTMLElement): HTMLInputElement {
  const input = container.querySelector('input[type="file"]');
  expect(input).not.toBeNull();
  return input as HTMLInputElement;
}

function pick(input: HTMLInputElement, files: File[]): void {
  Object.defineProperty(input, "files", { value: files, configurable: true });
  fireEvent.change(input);
}

function typeAndSubmit(text: string): void {
  const box = screen.getByPlaceholderText("Type your query here");
  fireEvent.change(box, { target: { value: text } });
  fireEvent.keyDown(box, { key: "Enter", keyCode: 13 });
}

beforeEach(() => {
  threadState.processMessage.mockReset().mockResolvedValue(undefined);
  threadState.isRunning = false;
  threadState.isLoadingMessages = false;
  threadState.messages = [];
  uploadMock.mockReset().mockResolvedValue({
    id: FILE_ID,
    mimeType: "image/png",
    filename: "note.png",
    url: `/api/files/${FILE_ID}/content`,
  });
  removeMock.mockReset().mockResolvedValue(undefined);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("ChatComposer attachments", () => {
  it("uploads a picked image and shows a thumbnail chip", async () => {
    const { container } = await renderComposer();
    pick(fileInput(container), [
      new File(["x"], "note.png", { type: "image/png" }),
    ]);
    const img = await screen.findByRole("img", { name: "note.png" });
    expect(img.getAttribute("src")).toBe(`/api/files/${FILE_ID}/content`);
    expect(uploadMock).toHaveBeenCalledTimes(1);
    expect(uploadMock.mock.calls[0]?.[0]).toBeInstanceOf(File);
  });

  it("refuses an image when the model has no vision; pdf still attaches", async () => {
    const { container } = await renderComposer({
      models: [{ id: "m-plain", name: "Plain", default: true, vision: false }],
    });
    pick(fileInput(container), [
      new File(["x"], "note.png", { type: "image/png" }),
    ]);
    expect(uploadMock).not.toHaveBeenCalled();
    expect(screen.getByRole("alert").textContent).toMatch(/vision/i);

    uploadMock.mockResolvedValue({
      id: FILE_ID,
      mimeType: "application/pdf",
      filename: "doc.pdf",
      url: `/api/files/${FILE_ID}/content`,
    });
    pick(fileInput(container), [
      new File(["x"], "doc.pdf", { type: "application/pdf" }),
    ]);
    await screen.findByText("doc.pdf");
    expect(uploadMock).toHaveBeenCalledTimes(1);
  });

  it("removes a chip through DELETE /api/files/{id}", async () => {
    const { container } = await renderComposer();
    pick(fileInput(container), [
      new File(["x"], "note.png", { type: "image/png" }),
    ]);
    await screen.findByRole("img", { name: "note.png" });
    fireEvent.click(screen.getByRole("button", { name: /remove note\.png/i }));
    expect(removeMock).toHaveBeenCalledWith(FILE_ID);
    expect(screen.queryByText("note.png")).toBeNull();
  });

  it("sends [text, binary...] content when chips are attached", async () => {
    const { container } = await renderComposer();
    pick(fileInput(container), [
      new File(["x"], "note.png", { type: "image/png" }),
    ]);
    await screen.findByRole("img", { name: "note.png" });
    typeAndSubmit("look at this");
    expect(threadState.processMessage).toHaveBeenCalledWith({
      role: "user",
      content: [
        { type: "text", text: "look at this" },
        {
          type: "binary",
          mimeType: "image/png",
          id: FILE_ID,
          filename: "note.png",
          url: `/api/files/${FILE_ID}/content`,
        },
      ],
    });
    // Sent chips clear; the file rows stay (the message owns them now).
    expect(screen.queryByText("note.png")).toBeNull();
    expect(removeMock).not.toHaveBeenCalled();
  });

  it("keeps the string content path when nothing is attached", async () => {
    await renderComposer();
    typeAndSubmit("plain text");
    expect(threadState.processMessage).toHaveBeenCalledWith({
      role: "user",
      content: "plain text",
    });
  });

  it("does not send while an upload is still in flight", async () => {
    uploadMock.mockReturnValue(new Promise(() => {}));
    const { container } = await renderComposer();
    pick(fileInput(container), [
      new File(["x"], "note.png", { type: "image/png" }),
    ]);
    await screen.findByText("note.png");
    typeAndSubmit("look at this");
    // The draft must not silently drop: nothing is sent, chip stays.
    expect(threadState.processMessage).not.toHaveBeenCalled();
    expect(screen.getByText("note.png")).not.toBeNull();
    expect(screen.getByText(/uploading/)).not.toBeNull();
  });

  it("deletes the file row when a chip is removed mid-upload", async () => {
    let resolveUpload!: (
      ref: Awaited<ReturnType<typeof uploadAttachment>>,
    ) => void;
    uploadMock.mockReturnValue(
      new Promise((resolve) => {
        resolveUpload = resolve;
      }),
    );
    const { container } = await renderComposer();
    pick(fileInput(container), [
      new File(["x"], "note.png", { type: "image/png" }),
    ]);
    const remove = await screen.findByRole("button", {
      name: /remove note\.png/i,
    });
    fireEvent.click(remove);
    expect(removeMock).not.toHaveBeenCalled();
    resolveUpload({
      id: FILE_ID,
      mimeType: "image/png",
      filename: "note.png",
      url: `/api/files/${FILE_ID}/content`,
    });
    await vi.waitFor(() =>
      expect(removeMock).toHaveBeenCalledWith(FILE_ID),
    );
  });

  it("enqueues {text, parts} while a run is in flight", async () => {
    const postBodies: string[] = [];
    const queue = makeQueueStore(postBodies);
    threadState.isRunning = true;
    const { container } = await renderComposer({ queue });
    pick(fileInput(container), [
      new File(["x"], "note.png", { type: "image/png" }),
    ]);
    await screen.findByRole("img", { name: "note.png" });
    typeAndSubmit("queued note");
    await vi.waitFor(() => expect(postBodies).toHaveLength(1));
    const body = JSON.parse(postBodies[0] ?? "{}") as {
      threadId: string;
      content: { text: string; parts?: unknown[] };
    };
    expect(body.threadId).toBe(THREAD);
    expect(body.content.text).toBe("queued note");
    expect(body.content.parts).toEqual([
      {
        type: "binary",
        mimeType: "image/png",
        id: FILE_ID,
        filename: "note.png",
        url: `/api/files/${FILE_ID}/content`,
      },
    ]);
    expect(threadState.processMessage).not.toHaveBeenCalled();
  });
});
