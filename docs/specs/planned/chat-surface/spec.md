# Chat surface

## Problem Statement

The authenticated app is a set of forms and tables. Users have no way to
ask questions, get help, or drive the product in natural language. The
team wants the product to feel like an AI chat app, with other views
around it. The LiteLLM gateway is deployed but no service calls it.

## Solution

A chat page at the private `/chat` route, built on the OpenUI
`AgentInterface` SDK. Replies stream. Threads persist in Postgres and
survive reloads. The chat follows the app theme, in light and dark.
The app gains a light theme alongside the current dark one, with a
toggle. All provider traffic flows through the BFF and the API. The
provider key never reaches the browser. App chrome stays base-nova.
OpenUI renders inside the chat canvas only.

## User Stories

1. As an authenticated member, I want a chat page in the app, so that I can
   work with an AI assistant without leaving the product.
2. As an authenticated member, I want replies to stream as they are
   generated, so that I see progress immediately.
3. As an authenticated member, I want to stop a running reply, so that I am
   not stuck waiting.
4. As an authenticated member, I want my conversations to survive a reload,
   so that I do not lose work.
5. As an authenticated member, I want a thread list in the chat sidebar, so
   that I can switch between conversations.
6. As an authenticated member, I want to start a new thread, so that topics
   stay separate.
7. As an authenticated member, I want to rename a thread, so that I can find
   it later.
8. As an authenticated member, I want to delete a thread, so that stale
   conversations do not pile up.
9. As an authenticated member, I want threads titled from my first message,
   so that the list is readable without effort.
10. As an authenticated member, I want older threads reachable by paging, so
    that history is not capped.
11. As an authenticated member, I want starter prompts on the empty state, so
    that I know what to ask first.
12. As an authenticated member, I want replies rendered as rich components
    such as steps and callouts, so that answers are easy to scan.
13. As an authenticated member, I want my threads visible only to me, so that
    privacy holds inside my tenant.
14. As a member of tenant A, I want my threads bound to my tenant context, so
    that data never leaks across tenants.
15. As an authenticated member, I want the chat to match the app theme, so
    that dark mode stays consistent everywhere.
16. As an authenticated member, I want a light mode with a toggle, so that I
    can pick what my eyes prefer.
17. As a tenant admin, I want chat to use the existing session and role
    system, so that no new auth path appears.
18. As an operator, I want the provider key to live only server side, so that
    the browser bundle holds no secrets.
19. As an operator, I want the gateway address and model set by env vars, so
    that I can change providers without a code change.
20. As an operator, I want a clear error in the chat when the gateway is
    down, so that users see a message, not a hang.
21. As a developer, I want the assistant reply stored when a stream ends or
    is aborted, so that a reload always matches what the user saw.
22. As an authenticated member on a phone, I want the chat layout to adapt,
    so that it is usable on small screens.

## Implementation Decisions

### Adoption

- Full adoption of the OpenUI React SDK: `@openuidev/react-ui`,
  `@openuidev/react-lang`, `@openuidev/react-headless` (plus the `zustand`
  peer). React 19 matches the peer requirement.
- The chat page renders `AgentInterface` with `openuiChatLibrary`, a title,
  and starter prompts. No hand-built chat components.
- App chrome (shell, nav, forms) stays base-nova. OpenUI styles are scoped to
  the chat canvas. The layered stylesheet variant is used, with the Tailwind
  v4 layer order declared once in the global stylesheet. The import lives in
  exactly one place, because Turbopack misorders layers with multiple import
  sites.

### Routes and modules

- Web: a chat page in the private route group at `/chat`. A nav link is
  added to the private shell. The dashboard stays the private root.
- Web: a chat client config module that builds the `fetchLLM` transport
  (`openAIMessageFormat` messages, `openAIAdapter()` OpenAI SSE stream
  adapter, URL `/api/chat`) and the `restStorage` adapter (base URL
  `/api/threads`, `openAIMessageFormat`).
- Web BFF: a chat completion proxy route and a threads CRUD proxy route.
  Both forward the session cookie to the API. The completion proxy streams
  bytes in both directions without buffering. It uses an extended timeout,
  because the shared proxy default of 30 seconds is too short. It passes the
  browser abort signal through to the API. The proxy helper gains an
  optional timeout parameter. All upstream address env reads stay inside the
  API route directory, per the BFF gate.
- API: a threads router and a chat router, registered like the existing
  routers. Both require a session and resolve the principal user and tenant.

### Threads contract (restStorage)

The API implements the five endpoints the SDK calls. Messages travel in the
OpenAI chat message shape on both storage and completion paths, so one shape
is stored, resent, and forwarded to the gateway.

| Operation     | Method and path                    | Body                 | Returns                    |
| ------------- | ---------------------------------- | -------------------- | -------------------------- |
| List threads  | `GET /api/threads/get?cursor=`     | none                 | `{ threads, nextCursor? }` |
| Create thread | `POST /api/threads/create`         | `{ messages: [...] }`| the new `Thread`           |
| Get messages  | `GET /api/threads/get/{threadId}`  | none                 | `Message[]`                |
| Update thread | `PATCH /api/threads/update/{id}`   | full `Thread`        | updated `Thread`           |
| Delete thread | `DELETE /api/threads/delete/{id}`  | none                 | empty, 204                 |

- `Thread` at the boundary: `{ id, title, createdAt, isPending? }`.
- Thread ids are server-generated UUIDs. `createdAt` is an epoch number.
- Titles are derived server side from the first user message text, capped in
  length. Update accepts a client rename but keeps owner scoping.
- Listing is keyset paginated on creation time and id. The cursor is opaque.
  Page size is fixed server side.
- Only the owner sees a thread. Rows also carry the tenant of the session,
  per ADR-0001 tenancy. The existing flush guard validates tenant stamps.

### Completion and persistence

- `POST /api/chat` (BFF) relays to the API completion endpoint. Body:
  `{ threadId, runId, messages }`. Response: OpenAI-compatible SSE,
  passed through unchanged from LiteLLM.
- The completion endpoint validates that the thread belongs to the caller.
  It caps message count and total size. It accepts only user, assistant, and
  system roles. It replaces the stored history with the validated incoming
  list. It calls the gateway with `stream: true`. It appends the assistant
  reply row when the stream closes.
- On client abort, the API cancels its gateway request. The partial
  assistant text is stored. A cancelled run is intentional and raises no
  error.
- A system prompt derived from the chat component library is prepended, so
  the model can emit chat components (steps, callouts, follow ups).
- Pre-stream gateway failure answers 502, which the chat surfaces as a
  thread error. A mid-stream failure emits an SSE error event and closes
  the stream. Stored history is left untouched in both cases.

### Schema

One migration creates two tables, per the extension-table pattern. No
columns are added to `User`.

- `chat_threads`: UUID id, `user_id` FK to users with cascade delete,
  `tenant_id` text (tenantable row per ADR-0001), title with length check,
  created and updated timestamps. Index on owner and creation time.
- `chat_messages`: UUID id, `thread_id` FK to chat threads with cascade
  delete, sequence number for ordering, role with a check constraint,
  JSONB content (one OpenAI chat message), created timestamp. Index on
  thread and sequence.

### Configuration

- A new frozen chat config group in the API config: gateway URL
  (`API_LITELLM_URL`, localhost default), gateway key
  (`API_LITELLM_API_KEY`), and model name (`API_CHAT_MODEL`, dev default).
  Dev values line up with the compose LiteLLM service. Prod values come from
  the deploy environment and must be mirrored like other env secrets.
- The web holds no LLM env vars at all. The gateway key exists only in the
  API process.

### Theming

- The web app gains a light palette next to the current dark one. The dark
  tokens move under the dark class variant. Default stays dark, so the
  current look is unchanged until the user toggles.
- A theme module owns the mode. It persists the choice in local storage. It
  applies the class on the root element before paint. It exposes the active
  mode to React. A toggle lives in the private shell.
- The chat reads the active mode and passes it to the OpenUI theme provider,
  so the chat is dark when the app is dark and light when the app is light.
- Brand colors map from our palette into the OpenUI theme object. Exact
  values are tuned visually during implementation.

## Testing Decisions

- Good tests assert external behavior at existing seams. No tests cover
  OpenUI internals; the SDK is third party. No DOM tests; the repo has none.
- API seam: HTTP tests through the test client against the test database,
  as in the registration and profile suites. A fake gateway upstream with
  canned SSE is injected at the completion module boundary, the only new
  test infrastructure. Tests assert: exact storage contract shapes, auth
  failures, owner isolation between users, tenant stamping, title
  derivation, cursor paging, history replacement per run, assistant row
  after stream close, partial storage on abort, pre-stream gateway failure
  answered 502, mid-stream failure surfacing the SSE error event, and
  stored history untouched in both failure cases.
- Migration: the real-Alembic scratch database test pattern covers the new
  revision.
- BFF seam: route tests with an injected fetch, as in the existing proxy
  tests. Tests assert cookie forwarding, byte-identical stream pass-through,
  the extended timeout, and that no provider key material can appear in
  responses.
- Web unit seam: the theme module and the chat client config module get
  Vitest unit tests, as other lib modules do.
- New tests run through `uvx falsegreen` and the test smell review before
  commit.

## Out of Scope

- Tools and function calling; generative domain components that render app
  views (a later spec).
- Artifacts channel of the storage contract.
- Shared, org-wide, or collaboratively edited threads.
- Message edit and regenerate controls.
- Rate limits, quotas, and token accounting.
- A model picker in the UI.
- Attachments, images, and voice.
- Making chat the private root; the dashboard keeps that role.

## Further Notes

- Visual map: `spec.html` beside this file shows the module shape, the depth
  before and after, and the test seams.
- The threads contract and self-hosting pattern come from the OpenUI docs
  consulted at 0.12.x; the installed pin is 0.17.0 exact, contract unchanged.
- The upstream proxy helper change (optional timeout) must stay backward
  compatible with the catch-all route.
- Ops follow up: add the two new `API_LITELLM_*` env vars to the prod API
  environment, or every chat call fails at deploy time.
