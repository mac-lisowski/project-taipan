// Chat model store: the allowed list comes from the API once per chat
// surface, the pick persists under a taipan-* key when the store was
// created with one, and completion requests read the current id live so
// a switch never rebuilds the ChatLLM.
export interface ChatModel {
  id: string;
  name: string;
  default?: boolean;
  // Capability flags from the API catalog; absent reads as unsupported.
  vision?: boolean;
  pdf_input?: boolean;
}

export type ChatModelStatus = "idle" | "loading" | "ready" | "error";

export interface ChatModelState {
  status: ChatModelStatus;
  models: ChatModel[];
  currentId: string | null;
}

export const CHAT_MODEL_STORAGE_KEY = "taipan-chat-model";
export const CHAT_MODELS_URL = "/api/chat/models";

const SERVER_STATE: ChatModelState = {
  status: "idle",
  models: [],
  currentId: null,
};

// A stored id wins only while the fetched list still contains it. The API
// marks its configured default; the first entry is the last resort.
export function resolveModelId(
  models: ChatModel[],
  stored: string | null,
): string | null {
  if (stored !== null && models.some((model) => model.id === stored)) {
    return stored;
  }
  return (models.find((model) => model.default) ?? models[0])?.id ?? null;
}

function isChatModelList(data: unknown): data is ChatModel[] {
  return (
    Array.isArray(data) &&
    data.every(
      (item) =>
        typeof item === "object" &&
        item !== null &&
        typeof (item as ChatModel).id === "string" &&
        typeof (item as ChatModel).name === "string",
    )
  );
}

export type ChatModelStore = {
  subscribe: (notify: () => void) => () => void;
  getSnapshot: () => ChatModelState;
  getServerSnapshot: () => ChatModelState;
  currentId: () => string | null;
  select: (id: string) => void;
  load: () => Promise<void>;
};

export function createChatModelStore(
  options: { storageKey?: string | null } = {},
): ChatModelStore {
  // Only a store built with a key persists and cross-tab syncs; a pane
  // store passes none so its pick can never reach the shared
  // taipan-chat-model entry or another tab's main chat.
  const storageKey = options.storageKey ?? null;
  let state: ChatModelState = SERVER_STATE;
  let inflight: Promise<void> | null = null;
  const listeners = new Set<() => void>();

  function emit(next: ChatModelState): void {
    state = next;
    listeners.forEach((notify) => notify());
  }

  function readStored(): string | null {
    if (storageKey === null) return null;
    try {
      return window.localStorage.getItem(storageKey);
    } catch {
      return null;
    }
  }

  function select(id: string): void {
    if (storageKey !== null) {
      try {
        window.localStorage.setItem(storageKey, id);
      } catch {
        // Storage blocked: the pick still holds for this session.
      }
    }
    emit({ ...state, currentId: id });
  }

  // Fetches once per store: repeat calls join the same flight, and an
  // error keeps the picker hidden until reload.
  function load(): Promise<void> {
    if (inflight !== null) return inflight;
    if (typeof window === "undefined") return Promise.resolve();
    emit({ ...state, status: "loading" });
    inflight = (async () => {
      try {
        const res = await fetch(CHAT_MODELS_URL);
        if (!res.ok) throw new Error(`models list answered ${res.status}`);
        const data: unknown = await res.json();
        if (!isChatModelList(data)) throw new Error("malformed models list");
        emit({
          status: "ready",
          models: data,
          currentId: resolveModelId(data, readStored()),
        });
      } catch {
        emit({ ...state, status: "error", models: [], currentId: null });
      }
    })();
    return inflight;
  }

  // Cross-tab sync mirrors the theme store: a foreign write re-reads
  // storage and re-resolves against the loaded list. Unkeyed stores
  // skip the listener because they never write storage.
  function subscribe(notify: () => void): () => void {
    listeners.add(notify);
    if (typeof window === "undefined" || storageKey === null) {
      return () => {
        listeners.delete(notify);
      };
    }
    function onStorage(event: StorageEvent): void {
      if (event.key !== storageKey) return;
      emit({ ...state, currentId: resolveModelId(state.models, readStored()) });
    }
    window.addEventListener("storage", onStorage);
    return () => {
      listeners.delete(notify);
      window.removeEventListener("storage", onStorage);
    };
  }

  return {
    subscribe,
    getSnapshot: () => state,
    getServerSnapshot: () => SERVER_STATE,
    currentId: () => state.currentId,
    select,
    load,
  };
}

// The main surface's store: the only instance holding the shared key.
// Non-React callers use it directly; React consumers read the store
// through chat-model-context.
export const chatModelStore = createChatModelStore({
  storageKey: CHAT_MODEL_STORAGE_KEY,
});
