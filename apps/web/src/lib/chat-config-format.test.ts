import type * as ReactHeadless from "@openuidev/react-headless";
import { describe, expect, it } from "vitest";

import { chatMessageFormat } from "./chat-config";

// The backend stores wire dicts verbatim; the real format collapses binary
// parts, so the wrapper must restore them. No SDK mocks needed: the format
// functions under test never touch the storage or stream factories.
describe("chat message format binary round-trip", () => {
  const binaryPart: ReactHeadless.BinaryInputContent = {
    type: "binary",
    mimeType: "image/png",
    id: "file-1",
    filename: "note.png",
    url: "/api/files/file-1/content",
  };
  const textPart: ReactHeadless.TextInputContent = {
    type: "text",
    text: "what is in this?",
  };
  const partsMessage: ReactHeadless.Message = {
    id: "m1",
    role: "user",
    content: [textPart, binaryPart],
  };

  it("keeps binary parts verbatim in the outbound wire body", () => {
    const wire = chatMessageFormat.toApi([
      partsMessage,
    ]) as unknown as Array<{ role: string; content: unknown[] }>;

    expect(wire[0]?.role).toBe("user");
    expect(wire[0]?.content).toEqual([
      { type: "text", text: "what is in this?" },
      binaryPart,
    ]);
  });

  it("restores binary parts from stored message dicts", () => {
    const stored = [
      { role: "user", content: [{ type: "text", text: "hi" }, binaryPart] },
    ];

    const messages = chatMessageFormat.fromApi(stored);

    expect(messages[0]?.content).toEqual([{ type: "text", text: "hi" }, binaryPart]);
    expect(messages[0]?.id).toEqual(expect.any(String));
  });

  it("keeps the part through a reload then resend", () => {
    const stored = [
      { role: "user", content: [{ type: "text", text: "hi" }, binaryPart] },
    ];
    const reloaded = chatMessageFormat.fromApi(stored);

    const resent = chatMessageFormat.toApi(reloaded) as unknown as Array<{
      content: unknown[];
    }>;

    expect(resent[0]?.content[1]).toEqual(binaryPart);
  });

  // Reload replay of save_artifact cards reads toolCalls off the stored
  // assistant message; the format must not drop them through fromApi.
  it("keeps tool_calls on stored assistant messages", () => {
    const stored = [
      {
        role: "assistant",
        content: "done",
        tool_calls: [
          {
            id: "call_1",
            type: "function",
            function: { name: "save_artifact", arguments: '{"title":"t"}' },
          },
        ],
      },
    ];

    const messages = chatMessageFormat.fromApi(stored);
    const assistant = messages[0] as ReactHeadless.AssistantMessage;

    expect(assistant.toolCalls).toEqual([
      {
        id: "call_1",
        type: "function",
        function: { name: "save_artifact", arguments: '{"title":"t"}' },
      },
    ]);
  });

  it("leaves string content and other roles untouched", () => {
    const stored = [
      { role: "user", content: "plain text" },
      { role: "assistant", content: "answer" },
    ];

    const messages = chatMessageFormat.fromApi(stored);
    const wire = chatMessageFormat.toApi(messages) as unknown as Array<{
      role: string;
      content: unknown;
    }>;

    expect(messages[0]?.content).toBe("plain text");
    expect(wire).toEqual([
      { role: "user", content: "plain text" },
      { role: "assistant", content: "answer" },
    ]);
  });
});
