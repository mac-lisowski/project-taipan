// @vitest-environment happy-dom

import type { UserMessage as UserMessageType } from "@openuidev/react-headless";
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { UserMessage } from "@/components/chat/message-attachments";

function message(content: UserMessageType["content"]): UserMessageType {
  return { id: "m1", role: "user", content };
}

afterEach(cleanup);

describe("UserMessage attachments", () => {
  it("renders an image binary part inline at its url", () => {
    const { container } = render(
      <UserMessage
        message={message([
          { type: "text", text: "see this" },
          {
            type: "binary",
            mimeType: "image/png",
            id: "f1",
            filename: "note.png",
            url: "/api/files/f1/content",
          },
        ])}
      />,
    );

    const img = container.querySelector("img");
    expect(img?.getAttribute("src")).toBe("/api/files/f1/content");
    expect(img?.getAttribute("alt")).toBe("note.png");
    expect(container.textContent).toContain("see this");
  });

  it("renders a non-image binary part as a download chip", () => {
    const { container } = render(
      <UserMessage
        message={message([
          {
            type: "binary",
            mimeType: "application/pdf",
            id: "f2",
            filename: "report.pdf",
            url: "/api/files/f2/content",
          },
        ])}
      />,
    );

    const link = container.querySelector("a");
    expect(link?.getAttribute("href")).toBe("/api/files/f2/content");
    expect(link?.textContent).toContain("report.pdf");
    expect(container.querySelector("img")).toBeNull();
  });

  it("falls back to the files content route when url is missing", () => {
    const { container } = render(
      <UserMessage
        message={message([
          { type: "binary", mimeType: "application/pdf", id: "f3", filename: "a.pdf" },
        ])}
      />,
    );

    expect(container.querySelector("a")?.getAttribute("href")).toBe(
      "/api/files/f3/content",
    );
  });

  it("never emits a stored non-web href", () => {
    for (const badUrl of ["javascript:alert(1)", "//evil.example/x.txt"]) {
      const { container, unmount } = render(
        <UserMessage
          message={message([
            {
              type: "binary",
              mimeType: "text/plain",
              id: "f4",
              filename: "x.txt",
              url: badUrl,
            },
          ])}
        />,
      );

      expect(container.querySelector("a")?.getAttribute("href")).toBe(
        "/api/files/f4/content",
      );
      unmount();
    }
  });

  it("renders plain string content as text", () => {
    const { container } = render(<UserMessage message={message("hello")} />);

    expect(container.textContent).toContain("hello");
    expect(container.querySelector("img, a")).toBeNull();
  });
});
