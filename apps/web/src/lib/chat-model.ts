// Chat model store: the allowed list comes from the API once per page
// load, the pick persists under a taipan-* key, and completion requests
// read the current id from here so a switch never rebuilds the ChatLLM.
export interface ChatModel {
  id: string;
  name: string;
  default?: boolean;
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

let state: ChatModelState = SERVER_STATE;
let inflight: Promise<void> | null = null;
const listeners = new Set<() => void>();

function emit(next: ChatModelState): void {
  state = next;
  listeners.forEach((notify) => notify());
}

export function readChatModelState(): ChatModelState {
  return state;
}

// The fetch wrapper in chat-config reads the id here, so the ChatLLM
// instance never has to be rebuilt for a model switch.
export function currentChatModelId(): string | null {
  return state.currentId;
}

function readStored(): string | null {
  try {
    return window.localStorage.getItem(CHAT_MODEL_STORAGE_KEY);
  } catch {
    return null;
  }
}

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

export function selectChatModel(id: string): void {
  try {
    window.localStorage.setItem(CHAT_MODEL_STORAGE_KEY, id);
  } catch {
    // Storage blocked: the pick still holds for this session.
  }
  emit({ ...state, currentId: id });
}

// Fetches once per page load: repeat calls join the same flight, and an
// error keeps the picker hidden until reload.
export function loadChatModels(): Promise<void> {
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
// storage and re-resolves against the loaded list.
function subscribe(notify: () => void): () => void {
  listeners.add(notify);
  if (typeof window === "undefined") {
    return () => {
      listeners.delete(notify);
    };
  }
  function onStorage(event: StorageEvent): void {
    if (event.key !== CHAT_MODEL_STORAGE_KEY) return;
    emit({ ...state, currentId: resolveModelId(state.models, readStored()) });
  }
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(notify);
    window.removeEventListener("storage", onStorage);
  };
}

export const chatModelStore = {
  subscribe,
  getSnapshot: readChatModelState,
  getServerSnapshot: (): ChatModelState => SERVER_STATE,
};
