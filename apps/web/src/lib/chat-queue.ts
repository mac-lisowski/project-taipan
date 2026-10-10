// Server-backed send queue for one thread: rows live behind the BFF, this
// store mirrors them and runs the falling-edge dispatch loop.

import type { MessagePart } from "@/lib/attachments";

export type QueueRow = {
  id: string;
  threadId: string;
  seq: number;
  // `parts` holds attachment binary parts only; QueueContent on the API is
  // extra="allow" so the key rides through verbatim.
  content: { text: string; parts?: MessagePart[] };
  createdAt: number;
};

export type QueueSend = (content: string | MessagePart[]) => Promise<void>;

export type QueueNotice = "enqueue-failed" | "sync-failed";

export type QueueDispatch = {
  id: string;
  text: string;
  /** The exact content passed to send; retries replay it as-is. */
  content: string | MessagePart[];
  attempts: number;
  /** noteRunStarted observed a rising edge carrying this dispatch's text. */
  started: boolean;
};

export type ChatQueueSnapshot = {
  threadId: string | null;
  rows: QueueRow[];
  dispatch: QueueDispatch | null;
  /** Head row whose dispatch exhausted its retry; offers a manual send. */
  failedId: string | null;
  notice: QueueNotice | null;
};

const EMPTY: ChatQueueSnapshot = {
  threadId: null,
  rows: [],
  dispatch: null,
  failedId: null,
  notice: null,
};

const QUEUE_BASE = "/api/threads/queue";
// First try plus one retry, then the row waits for a manual send.
const MAX_ATTEMPTS = 2;
const JSON_HEADERS = { "content-type": "application/json" };

const bySeq = (a: QueueRow, b: QueueRow): number => a.seq - b.seq;

export function createChatQueueStore(fetchImpl: typeof fetch = fetch) {
  let snapshot = EMPTY;
  const listeners = new Set<() => void>();

  function set(patch: Partial<ChatQueueSnapshot>): void {
    snapshot = { ...snapshot, ...patch };
    listeners.forEach((notify) => notify());
  }

  // Shared fetch shape: one notice per operation, 404 tolerated on delete
  // because the row is gone either way.
  async function request(
    path: string,
    notice: QueueNotice,
    apply: (res: Response) => Promise<void> | void,
    init?: RequestInit,
    tolerate404 = false,
  ): Promise<boolean> {
    try {
      const res = await fetchImpl(`${QUEUE_BASE}${path}`, init);
      if (!res.ok && !(tolerate404 && res.status === 404)) {
        set({ notice });
        return false;
      }
      await apply(res);
      return true;
    } catch {
      set({ notice });
      return false;
    }
  }

  async function hydrate(threadId: string | null): Promise<void> {
    // Re-hydrating the same thread must not drop an in-flight dispatch.
    set(snapshot.threadId === threadId ? { notice: null } : { ...EMPTY, threadId });
    if (!threadId) return;
    await request(`/get?thread_id=${encodeURIComponent(threadId)}`, "sync-failed", async (res) => {
      const rows = (await res.json()) as QueueRow[];
      // A slow reply must not clobber a newer thread or resurrect a row a
      // dispatch already consumed.
      if (snapshot.threadId === threadId && !snapshot.dispatch)
        set({ rows: rows.slice().sort(bySeq) });
    });
  }

  // Returns whether the row was stored so the caller can drop its draft.
  // `parts` carries attachment binary parts; the composer already uploaded
  // them, so a queued send needs no upload machinery of its own.
  async function enqueue(text: string, parts?: MessagePart[]): Promise<boolean> {
    const threadId = snapshot.threadId;
    if (!threadId) return false;
    return request(
      "/create",
      "enqueue-failed",
      async (res) => {
        const created = (await res.json()) as QueueRow;
        // A reply for a thread the user already left must not land here.
        if (created.threadId === snapshot.threadId)
          set({ rows: [...snapshot.rows, created].sort(bySeq), notice: null });
      },
      {
        method: "POST",
        headers: JSON_HEADERS,
        body: JSON.stringify({
          threadId,
          content: parts?.length ? { text, parts } : { text },
        }),
      },
    );
  }

  async function update(id: string, text: string): Promise<void> {
    // The API replaces content wholesale, so a parts row re-sends them or
    // the attachments would silently drop on edit.
    const parts = snapshot.rows.find((r) => r.id === id)?.content.parts;
    const content = parts?.length ? { text, parts } : { text };
    await request(
      `/update/${id}`,
      "sync-failed",
      async (res) => {
        const updated = (await res.json()) as QueueRow;
        set({ rows: snapshot.rows.map((r) => (r.id === id ? updated : r)) });
      },
      { method: "PATCH", headers: JSON_HEADERS, body: JSON.stringify({ content }) },
    );
  }

  async function remove(id: string): Promise<void> {
    await request(
      `/delete/${id}`,
      "sync-failed",
      () => {
        set({
          rows: snapshot.rows.filter((r) => r.id !== id),
          failedId: snapshot.failedId === id ? null : snapshot.failedId,
        });
      },
      { method: "DELETE" },
      true,
    );
  }

  // The row drops locally first so the chip does not linger while the
  // DELETE is in flight; a failed request leaves a ghost the user removes.
  async function deleteDispatched(id: string): Promise<void> {
    set({ rows: snapshot.rows.filter((r) => r.id !== id) });
    await request(
      `/delete/${id}`,
      "sync-failed",
      () => {},
      { method: "DELETE" },
      true,
    );
  }

  // Sends the head row. Called on a falling edge (via handleRunEnd) and on
  // manual send; both paths share the same guards.
  function dispatchHead({ send }: { send: QueueSend }): void {
    const head = snapshot.rows[0];
    if (!snapshot.threadId || !head || snapshot.dispatch) return;
    // A parts row rebuilds the message the composer would have sent:
    // text part first, then one binary part per attachment.
    const content: string | MessagePart[] = head.content.parts?.length
      ? [{ type: "text", text: head.content.text }, ...head.content.parts]
      : head.content.text;
    set({
      dispatch: {
        id: head.id,
        text: head.content.text,
        content,
        attempts: 1,
        started: false,
      },
      failedId: null,
    });
    void send(content).catch(() => {});
  }

  // The coordinator calls this on a rising edge whose last user message is
  // the dispatched text, which is the only attribution the SDK exposes.
  function noteRunStarted(sentText: string | null): void {
    const active = snapshot.dispatch;
    if (!active || active.started || sentText !== active.text) return;
    set({ dispatch: { ...active, started: true } });
    // Spec flow: the row is deleted once the run starts, because the text
    // now lives in thread history; a later run error is a chat concern.
    void deleteDispatched(active.id);
  }

  function handleRunEnd(end: { send: QueueSend; threadId: string | null }): void {
    if (!snapshot.threadId || snapshot.threadId !== end.threadId) return;
    const active = snapshot.dispatch;
    if (active?.started) {
      // The row is already consumed; an errored or aborted run shows as a
      // normal chat error, so the loop continues with the next head.
      set({ dispatch: null });
      dispatchHead({ send: end.send });
      return;
    }
    if (active) {
      // Never accepted: the send early-returned on a busy lane. Retry once,
      // then keep the row and flag it for a manual send.
      if (active.attempts < MAX_ATTEMPTS) {
        set({ dispatch: { ...active, attempts: active.attempts + 1 } });
        void end.send(active.content).catch(() => {});
        return;
      }
      set({ dispatch: null, failedId: active.id });
      return;
    }
    dispatchHead({ send: end.send });
  }

  return {
    subscribe(notify: () => void): () => void {
      listeners.add(notify);
      return () => {
        listeners.delete(notify);
      };
    },
    getSnapshot: (): ChatQueueSnapshot => snapshot,
    getServerSnapshot: (): ChatQueueSnapshot => EMPTY,
    hydrate,
    enqueue,
    update,
    remove,
    dispatchHead,
    noteRunStarted,
    handleRunEnd,
  };
}

export type ChatQueueStore = ReturnType<typeof createChatQueueStore>;

// The main surface's store: also the default context value in
// chat-queue-context, so an unwrapped tree behaves as before.
export const chatQueue = createChatQueueStore();
