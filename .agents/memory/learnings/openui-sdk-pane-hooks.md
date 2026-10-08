# OpenUI SDK (@openuidev/react-ui 0.17.0) pane-relevant internals

Verified against installed source (package ships src/ + dist).

- `AgentInterface.Route` children replace the whole thread region; mutual
  exclusive with thread view. Stream survives (store lives in ChatProvider).
- `slots.rest`: any non-slot direct child of `<AgentInterface>` renders as a
  permanent flex sibling inside `.openui-agent-container` (after thread/route
  block, inside all providers). Undocumented but stable pane hook; never
  remounts on nav. Wrap children in a plain div (direct-children extraction).
- DetailedView system: `useDetailedView(viewId)` + `DetailedViewPanel` portal
  into `[chat | separator | panel]` split inside `ThreadContainer` - works on
  Route views too. Free resize + ARIA + mobile overlay + sidebar auto-hide.
  But: single active view, resets to null on every `selectedThreadId` change
  (headless index.mjs ~2877), chat clamps to 420px initial, opening/closing
  force-toggles `isSidebarOpen`.
- `Container` measures own width via ResizeObserver: <768px = mobile layout
  (sidebar = hidden overlay + MobileHeader), >768 = fullscreen. A half-width
  second `AgentInterface` gets mobile chrome - compact chat with off-canvas
  thread list for free.
- Sidebar always renders (no removal prop; `{null}` children leave 272px
  chrome). Two instances: all stores/providers are per-instance; nested
  `ChatProvider` = independent threads. Theme collision only if themes differ.
- `AgentInterface` has no className/style prop; root is `height:100dvh` -
  inside a pane wrapper override `.pane .openui-agent-container{height:100%}`.
- `AgentInterface.Messages/ScrollArea/Composer` work under a bare
  `ChatProvider`; `ThreadList/NewChatButton/ThreadHeader/MobileHeader/
  SidebarItem` need the unexported `AgentInterfaceStoreProvider`.
- `restStorage` stateless, threadId-keyed; `selectedThreadId` is in-memory per
  instance. Two instances can show different threads; list mutations don't
  cross-refresh.
- chat-app.tsx `syncUrl` uses replaceState and strips query params - must
  merge `?pane=` when pane state goes in the URL.
