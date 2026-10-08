import {
  fetchLLM,
  openAIAdapter,
  openAIMessageFormat,
  restStorage,
} from "@openuidev/react-headless";

// Browser-facing BFF routes only: the API upstream is never addressed here.
export const CHAT_COMPLETION_URL = "/api/chat";
export const THREADS_BASE_URL = "/api/threads";

export function chatLLM() {
  return fetchLLM({
    url: CHAT_COMPLETION_URL,
    streamAdapter: openAIAdapter(),
    messageFormat: openAIMessageFormat,
  });
}

export function chatStorage() {
  return restStorage({
    baseUrl: THREADS_BASE_URL,
    messageFormat: openAIMessageFormat,
  });
}
