# Queue row deleted at run start, attributed by text match

`processMessage` appends the user message and flips `isRunning` in the
same synchronous set, resolves at run end, and never rejects. So the
spec's "delete the row once the run starts" is implemented in
`noteRunStarted`: the rising edge is only attributed to a pending
dispatch when the run's last user message text equals the dispatched
text. An unrelated run cannot consume the row.

Consequences:

- Retry applies only to sends that never started (processMessage
  early-returned on a busy lane). A started run that errors has its
  text in history already; resending would duplicate the user
  message, so the loop just moves to the next head.
- `threadError` is not read at all: it resets on every run start and
  a started run's error is a normal chat error, not a queue failure.
