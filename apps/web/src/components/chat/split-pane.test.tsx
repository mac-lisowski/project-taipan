// @vitest-environment happy-dom
//
// The repo's one DOM smoke test. It guards the undocumented SDK rest
// slot: a non-slot child of AgentInterface must render inside
// .openui-agent-container as a flex sibling of the thread region, or the
// pane detaches on an SDK upgrade. Deliberate exception to the unit-only
// rule, called out in the spec's Testing Decisions.

import { AgentInterface } from "@openuidev/react-ui";
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SplitPane } from "@/components/chat/split-pane";
import { ShellAccountProvider } from "@/components/shell/shell-context";
import { chatLLM, chatStorage } from "@/lib/chat-config";
import { PaneStateProvider } from "@/lib/pane-state-context";

// happy-dom lacks ResizeObserver; the separator needs one to measure.
if (typeof globalThis.ResizeObserver === "undefined") {
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
}

const ACCOUNT = {
  id: 1,
  email: "owner@example.com",
  tenant: "acme",
  roles: [],
  systemRoles: ["system_owner"],
};

function renderSurface(search: string) {
  window.history.replaceState(null, "", `/chat${search}`);
  return render(
    <ShellAccountProvider account={ACCOUNT}>
      <PaneStateProvider systemRoles={ACCOUNT.systemRoles}>
        <AgentInterface
          llm={chatLLM()}
          storage={chatStorage(null)}
          agentName="taipan"
        >
          <SplitPane />
        </AgentInterface>
      </PaneStateProvider>
    </ShellAccountProvider>,
  );
}

afterEach(cleanup);

describe("split pane rest-slot mount", () => {
  it("renders the pane inside the SDK container, beside the thread", async () => {
    const { container } = renderSurface("?pane=chat");
    const pane = await vi.waitFor(() => {
      const el = container.querySelector("#taipan-pane");
      expect(el).not.toBeNull();
      return el as HTMLElement;
    });
    // Direct child of the SDK root: the rest slot, not a portal.
    const root = pane.parentElement as HTMLElement;
    expect(root.classList.contains("openui-agent-container")).toBe(true);
    // The main chat subtree survives the pane mount: sidebar and thread
    // region sit beside the pane, untouched by the nested instance.
    const siblings = [...root.children].filter((el) => el !== pane);
    expect(
      siblings.some((el) =>
        el.classList.contains("openui-agent-sidebar-container"),
      ),
    ).toBe(true);
    expect(
      siblings.some((el) =>
        el.classList.contains("openui-agent-thread-container"),
      ),
    ).toBe(true);
  });

  it("mounts the nested chat inside the pane on ?pane=chat", async () => {
    const { container } = renderSurface("?pane=chat");
    const pane = await vi.waitFor(() => {
      const el = container.querySelector("#taipan-pane");
      expect(el).not.toBeNull();
      return el as HTMLElement;
    });
    // The nested instance scopes under .taipan-pane, where globals.css
    // pins its root to pane height instead of the viewport.
    expect(
      pane.querySelector(".openui-agent-container"),
    ).not.toBeNull();
  });

  it("stays unmounted when the URL carries no pane param", () => {
    const { container } = renderSurface("");
    expect(container.querySelector("#taipan-pane")).toBeNull();
    expect(container.querySelector(".openui-agent-container")).not.toBeNull();
  });
});
