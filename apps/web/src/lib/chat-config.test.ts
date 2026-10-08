import { afterEach, describe, expect, it, vi } from "vitest";

// The SDK factories are mocked so the test can pin the exact wiring the
// config module hands to AgentInterface.
const mocks = vi.hoisted(() => {
  const ADAPTER = { stream: true };
  const FORMAT = { wire: true };
  return {
    ADAPTER,
    FORMAT,
    fetchLLM: vi.fn(() => ({ kind: "llm" })),
    restStorage: vi.fn(() => ({ kind: "storage" })),
    openAIAdapter: vi.fn(() => ADAPTER),
  };
});

vi.mock("@openuidev/react-headless", () => ({
  fetchLLM: mocks.fetchLLM,
  restStorage: mocks.restStorage,
  openAIAdapter: mocks.openAIAdapter,
  openAIMessageFormat: mocks.FORMAT,
}));

import { chatLLM, chatStorage } from "./chat-config";

describe("chat client config", () => {
  afterEach(() => {
    mocks.fetchLLM.mockClear();
    mocks.restStorage.mockClear();
    mocks.openAIAdapter.mockClear();
  });

  it("wires the llm transport to the chat BFF route in OpenAI shape", () => {
    chatLLM();
    expect(mocks.fetchLLM).toHaveBeenCalledWith({
      url: "/api/chat",
      streamAdapter: mocks.ADAPTER,
      messageFormat: mocks.FORMAT,
    });
  });

  it("wires thread storage to the threads BFF route in OpenAI shape", () => {
    chatStorage();
    expect(mocks.restStorage).toHaveBeenCalledWith({
      baseUrl: "/api/threads",
      messageFormat: mocks.FORMAT,
    });
  });
});
