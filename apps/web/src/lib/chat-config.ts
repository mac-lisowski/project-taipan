import {
  fetchLLM,
  openAIAdapter,
  openAIMessageFormat,
  restStorage,
} from "@openuidev/react-headless";

import { currentChatModelId } from "./chat-model";

// Browser-facing BFF routes only: the API upstream is never addressed here.
export const CHAT_COMPLETION_URL = "/api/chat";
export const THREADS_BASE_URL = "/api/threads";

// Reads the model id live so a switch never rebuilds the ChatLLM and
// resets SDK stream state; unset id means the API default applies.
const modelBodyFetch: typeof fetch = (input, init) => {
  const model = currentChatModelId();
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

export function chatLLM() {
  return fetchLLM({
    url: CHAT_COMPLETION_URL,
    streamAdapter: openAIAdapter(),
    messageFormat: openAIMessageFormat,
    fetch: modelBodyFetch,
  });
}

export function chatStorage() {
  return restStorage({
    baseUrl: THREADS_BASE_URL,
    messageFormat: openAIMessageFormat,
  });
}
