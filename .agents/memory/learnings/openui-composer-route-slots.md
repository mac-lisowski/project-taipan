# OpenUI 0.17.0: composer unmounts on Route views; slots.rest stays mounted

- `AgentInterfaceBody` renders `activeRoute ? <ThreadContainer>{route
  children}</ThreadContainer> : <>{thread + composer}</>` (dist
  index.mjs ~6266). A Route match replaces the whole thread region:
  `<AgentInterface.Composer>` children unmount on /dashboard etc.
- Children that match no slot type land in `slots.rest` (extractSlots,
  index.mjs ~6083) and render inside `Container` on every view. A
  headless coordinator component placed there keeps effects alive.
- `useChatStore` is internal (index.mjs ~925, not in the export list):
  `isRunning`/`threadError` are only readable as hook snapshots. Feed
  them to non-React stores at edge time, not as imperative getters.
- `processMessage`: sets `isRunning` true synchronously, resolves at
  run end, never rejects; errors land in `threadError` (null on abort).
- `ConversationStarter` and `useComposerState` are not exported; Mode C
  composer children get no props.
