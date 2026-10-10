import {
  fetchLLM,
  openAIAdapter,
  openAIMessageFormat,
  restStorage,
  type BinaryInputContent,
  type ChatStorage,
  type Message,
  type MessageFormat,
  type Thread,
  type ThreadStorage,
} from "@openuidev/react-headless";

import { artifactStorage } from "./artifact-storage";
import { chatModelStore, type ChatModelStore } from "./chat-model";

// Browser-facing BFF routes only: the API upstream is never addressed here.
export const CHAT_COMPLETION_URL = "/api/chat";
export const THREADS_BASE_URL = "/api/threads";

// One server-rendered page of threads; null means fetch on mount.
export type ThreadSeed = { threads: Thread[]; nextCursor?: string };

// Reads the model id live off the given store so a switch never rebuilds
// the ChatLLM and resets SDK stream state; unset id means the API
// default applies.
function modelBodyFetch(store: ChatModelStore): typeof fetch {
  const wrapped: typeof fetch = (input, init) => {
    const model = store.currentId();
    // fetchLLM passes (url, init) with a stringified JSON body; a Request
    // input or non-string body cannot carry the id and degrades to default.
    if (model === null || typeof init?.body !== "string") {
      return fetch(input, init);
    }
    try {
      const parsed: unknown = JSON.parse(init.body);
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        return fetch(input, init);
      }
      return fetch(input, {
        ...init,
        body: JSON.stringify({ ...(parsed as Record<string, unknown>), model }),
      });
    } catch {
      // A body that is not JSON cannot carry the id; send it as-is.
      return fetch(input, init);
    }
  };
  return wrapped;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isBinaryPart(part: unknown): part is BinaryInputContent {
  return (
    isRecord(part) &&
    part.type === "binary" &&
    typeof part.mimeType === "string"
  );
}

// openAIMessageFormat maps user content parts 1:1, so an index zip restores binary slots.
function withBinaryOutbound(source: Message, wire: unknown): unknown {
  if (source.role !== "user" || !Array.isArray(source.content)) return wire;
  if (!isRecord(wire) || !Array.isArray(wire.content)) return wire;
  const converted = wire.content;
  return {
    ...wire,
    content: source.content.map((part, i) =>
      isBinaryPart(part) ? part : (converted[i] ?? part),
    ),
  };
}

function withBinaryInbound(message: Message, raw: unknown): Message {
  if (message.role !== "user" || !Array.isArray(message.content)) {
    return message;
  }
  if (!isRecord(raw) || !Array.isArray(raw.content)) return message;
  const source = raw.content;
  return {
    ...message,
    content: message.content.map((part, i) => {
      const stored = source[i];
      return isBinaryPart(stored) ? stored : part;
    }),
  };
}

// The API resolves binary parts server side and stores wire dicts verbatim; the SDK format collapses them.
export const chatMessageFormat: MessageFormat = {
  toApi(messages) {
    const wire = openAIMessageFormat.toApi(messages);
    const list = Array.isArray(wire) ? wire : [];
    return messages.map((message, i) => withBinaryOutbound(message, list[i]));
  },
  fromApi(data) {
    const raw = Array.isArray(data) ? data : [];
    return openAIMessageFormat
      .fromApi(data)
      .map((message, i) => withBinaryInbound(message, raw[i]));
  },
};

// The default is the main surface's singleton; a pane hands in its own
// store so its completions carry its own pick.
export function chatLLM(store: ChatModelStore = chatModelStore) {
  return fetchLLM({
    url: CHAT_COMPLETION_URL,
    streamAdapter: openAIAdapter(),
    messageFormat: chatMessageFormat,
    fetch: modelBodyFetch(store),
  });
}

// The seed answers only the first cursorless list call; later pages stay client side.
export function chatStorage(seed: ThreadSeed | null = null): ChatStorage {
  const inner = restStorage({
    baseUrl: THREADS_BASE_URL,
    messageFormat: chatMessageFormat,
  });
  let pending: ThreadSeed | null = seed;
  const thread: ThreadStorage = {
    ...inner.thread,
    listThreads(cursor?: string) {
      if (cursor === undefined && pending !== null) {
        const seeded = pending;
        pending = null;
        return Promise.resolve(seeded);
      }
      return inner.thread.listThreads(cursor);
    },
  };
  return { ...inner, thread, artifact: artifactStorage };
}
