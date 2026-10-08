# Split screen

## Problem Statement

The authenticated app is one full-viewport chat surface. App views render
inside it as routes, so the chat and a page never share the screen. When a
member opens the users list or settings, the chat disappears while a reply
may still stream invisibly. There is no way to watch a conversation and
work in a page at once, and no way to see two threads side by side.

## Solution

A resizable pane on the right edge of the authenticated surface. The pane
shows either an app view navigated inside the pane, or a second,
independent chat with its own thread. The main region keeps working as
today. The split ratio drags to any width and persists in the browser,
matching how the sidebar state persists today. The pane state lives in
the URL, so a reload or a shared link restores the screen. Below tablet
width the pane collapses to a full overlay, matching how other chat
products handle small screens.

## User Stories

1. As an authenticated member, I want to open a second pane on the right
   half of the screen, so that I can see two things at once.
2. As an authenticated member, I want the pane to show an app view such as
   the users list, so that I can browse the app while my chat stays open.
3. As an authenticated member, I want to navigate inside the pane between
   views, so that the pane acts like a second window into the app.
4. As an authenticated member, I want the pane to show a second chat with
   its own thread, so that I can compare conversations or multitask.
5. As an authenticated member, I want each chat to keep its own thread
   selection, so that the two sides never fight over one thread.
6. As an authenticated member, I want replies in both chats to stream at
   the same time, so that neither side blocks the other.
7. As an authenticated member, I want to drag the divider to any ratio,
   so that I can give more room to whichever side matters.
8. As an authenticated member, I want my split ratio and open state to
   survive a reload, so that the screen comes back as I left it.
9. As an authenticated member, I want the pane content encoded in the
   URL, so that I can share or restore a split screen by link.
10. As an authenticated member, I want to close the pane from its header,
    so that single-pane work is one click away.
11. As an authenticated member, I want a running reply to keep streaming
    while I open, resize, or close the pane, so that no work is lost.
12. As an authenticated member, I want the pane and the main region to
    share the app theme, so that both sides look like one product.
13. As an authenticated member on a small screen, I want the pane to
    become a full overlay instead of a split, so that nothing is
    cramped or unreachable.
14. As a member without the owner role, I want owner-only views refused
    inside the pane, so that role gates hold on every surface.
15. As an operator, I want the second chat to use the same session,
    tenant, and BFF paths, so that no new auth or data path appears.
16. As a developer, I want pane state handled by a pure state module,
    so that behavior is testable without a browser.
17. As a developer, I want the feature to depend on verified SDK
    behavior with a fallback documented, so that an SDK upgrade cannot
    silently break the layout.

## Implementation Decisions

### Pane model

- One `AgentInterface` instance owns the screen. The pane is a direct,
  non-slot child of it. The SDK collects unrecognized children into a
  rest list and renders them as permanent flex siblings inside its root
  container, inside all providers. This is undocumented behavior,
  verified in the installed 0.17.0 source. The pane therefore never
  remounts on navigation or thread switch.
- Rejected: two top-level `AgentInterface` instances. The SDK measures
  its own container width and switches to mobile chrome below 768px,
  so a half-width instance needs a viewport over roughly 1536px to keep
  desktop chrome, and every pane would duplicate the sidebar and thread
  list.
- Rejected: the SDK detailed-view system (`useDetailedView`,
  `DetailedViewPanel`). It renders a resizable side panel on every
  surface. It also closes on every thread switch. It allows one active
  view at a time. It clamps the chat to a fixed width on open. It
  mutates the sidebar open state. It suits transient detail panels,
  not a persistent pane. It remains the documented fallback if the
  rest-slot mechanism ever breaks.
- Rejected: Next.js parallel routes (every private page mounts its own
  chat surface, so slots cannot share one layout state; refresh also
  loses unmatched slot state), iframes (double runtime, shared history
  problems), the SDK workspace rail (renders only in the thread view).

### Pane state

- A pure state module owns the pane model: open or closed, content kind
  (`chat` or `view`), the pane-internal view path, optional detail
  selection inside a view, the split ratio, and which pane actions are
  legal from each state.
- Default ratio is one half. Allowed range keeps the chat region at or
  above its minimum viable width (roughly 360px) and the pane at or
  above the same floor.
- The URL is the single source of truth for open state and content on
  load. Local storage persists only the ratio and the last-used content
  (kind and view path), which seed the next manual open. This avoids a
  stored open flag racing the URL.
- The content kind and view path serialize into the `pane` query
  parameter. Thread selection inside a pane chat stays client state;
  the URL carries `pane=chat`, not a thread id.

### URL contract

- `?pane=view:/users` opens the pane on the users view. `?pane=chat`
  opens a second chat. No parameter means closed. Closing the pane
  removes the parameter.
- An unknown or role-forbidden pane path drops the parameter; the pane
  stays closed rather than showing an error surface.
- The parameter is meaningful only on chat-surface paths. Other routes
  ignore it.
- The existing URL sync writes the main view path with `replaceState`.
  It must merge the query string instead of replacing the whole URL.
- On mount, the shell reads the parameter and restores the pane.
  Browser history is not touched by pane actions; the back button keeps
  its chronological whole-screen semantics.
- The same view on both sides is allowed. The two surfaces stay
  independent.
- The parameter restores kind and view path only. Detail selections
  inside a view and the pane chat's thread choice do not round-trip;
  a reload or shared link reopens the pane on a fresh state. This is
  a deliberate v1 limit.

### Pane contents

- View kind: a small router maps the pane path to the existing view
  components (overview, users, settings, account, user detail). They
  are plain components with no SDK dependency, so they mount as-is
  inside a pane-owned scroll frame.
- Chat kind: a nested `AgentInterface` with its own provider, built
  from the same LLM and storage adapters, the same theme object, and
  the same message components, starters, and agent name as the main
  chat. All SDK stores are per instance, so threads, streams, and
  selection are fully independent. Below 768px of pane width the
  nested instance renders the SDK's mobile chrome: a hidden sidebar
  behind a menu and a mobile header, which supplies a compact thread
  picker for free. At pane widths of 768px and above the nested
  instance shows full desktop chrome, including its own sidebar thread
  list. That sidebar is the intended thread picker on wide panes.
- Both sides stream concurrently. The BFF relays are stateless per
  request with no per-session locks, so two streams need no backend
  change.
- The nested chat mounts lazily on first use and stays mounted for the
  life of the surface. Closing the pane hides it without unmounting, so
  a running reply survives and reopening resumes the same thread.
- The SDK hardcodes viewport height on its root element; the pane
  overrides that to the pane height.
- Both instances share one theme object, so no theme-style collision
  occurs.

### Divider and layout

- A custom drag separator sits between the main region and the pane.
  It follows the WAI-ARIA window-splitter pattern: focusable,
  `role="separator"`, arrow keys for steps, Home and End for bounds.
  The SDK ships the same pattern internally but does not export it.
- The main region keeps its normal flex sizing; the pane takes a fixed
  flex basis of the chosen ratio. The root container keeps full
  viewport width, so the SDK never leaves desktop layout.
- The width floors apply to the thread region alone, after the fixed
  sidebar. The maximum pane width is the container minus the sidebar
  (about 272px) minus the thread floor (about 360px). Below roughly
  1264px viewport the maximum ratio is under one half; the chosen
  ratio clamps instead of breaking layout.

### Navigation rules inside panes

- All navigation inside a pane goes through pane state, never through
  real router navigation. A real navigation remounts the whole chat
  surface and kills running streams.
- The SDK navigation hook cannot serve inside a pane: it resolves the
  nearest SDK nav provider, which is always the main region's, and the
  provider itself is not exported. Views shared between the main region
  and the pane instead call an app-owned shell-navigation abstraction,
  provided per surface. On the main surface it delegates to the SDK
  hook; inside the pane it writes pane state.
- Two existing views use real navigation for internal moves and must be
  converted to that abstraction before they can live in a pane: the
  overview link to account and the user-detail fallback. The
  user-detail view already accepts a back callback; only its no-prop
  fallback navigates for real.

### Role gating

- The pane router applies the same role check as the sidebar nav source:
  owner-only paths are refused or hidden for non-owners. Page-level
  guards stay in place for direct URL loads.

### Entry points

- Sidebar nav items gain an open-in-pane affordance.
- The thread header area gains a split action that opens a second chat
  in the pane.
- The pane header carries a title, a back control for view navigation,
  and a close button.

### Small-screen behavior

- Below roughly 1024px viewport the split is not offered: the open
  affordances hide. An open pane degrades to a full-width overlay over
  the main region, closable, rather than a cramped split.

### SDK guards

- `artifactAutoOpen` is disabled on the main interface so that no
  future artifact renderer can commandeer the detailed-view slot that
  this design avoids but the SDK still manages.
- The SDK pin stays exact; a smoke test of pane rendering covers the
  undocumented rest-slot mechanism against upgrades.

### File budget

- The chat app module is already near the file-size gate. Pane wiring,
  entry points, and state glue live in new modules; the chat app gains
  composition lines only. If it still approaches the cap, the slot
  composition extracts into its own module.

## Testing Decisions

- Good tests assert external behavior at existing seams. The repo has
  no DOM component tests, so none are added.
- The pane state module gets Vitest unit tests, following the
  sidebar-state test pattern (stubbed window and local storage,
  module reload for state isolation). Tests assert: open and close
  transitions, kind switching, view path and detail-id rules, ratio
  clamping at both bounds, `pane` parameter round trips both ways,
  local storage persistence, and that non-owner roles cannot reach
  owner view paths.
- The `syncUrl` merge gets a unit test: pane parameter survives main
  navigation and is dropped when the pane closes.
- BFF and API are untouched; no HTTP tests are added.
- New tests run through `uvx falsegreen` and the test smell review
  before commit.

## Out of Scope

- More than two panes, vertical splits, and drag-and-drop between panes.
- A shared-input model-compare mode; the two chats stay independent.
- SDK detailed views and artifact features; the detailed-view system is
  left for its own later spec.
- Per-pane browser-history stacks.
- Split on phones; small screens get an overlay at most.
- Moving app views off SDK routes in the main region.
- Server persistence of pane layout; local storage is enough.

## Further Notes

- Visual map: `spec.html` beside this file shows the layout shape, the
  rejected alternatives, and the test seam.
- The rest-slot mechanism is undocumented. Record the choice and the
  fallback (SDK detailed view) in an ADR when the spec is accepted.
- Research behind the option picks: chat-plus-page surfaces in VS Code,
  Copilot, Gemini, and Microsoft 365 use a docked resizable panel;
  symmetric splits appear mainly in model-compare tools. Two independent
  chat panes are rare in mainstream chat apps, which route the need to
  pop-out windows. This spec serves both cases with one pane model.
