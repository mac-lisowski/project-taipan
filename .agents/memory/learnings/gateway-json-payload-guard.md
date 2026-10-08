# Guard gateway JSON before iterating

- `response.json().get("data", [])` can return a non-list; iterating
  it raised TypeError that escaped as a 500 (model switcher round-1
  finding). `isinstance`-check `data` and each item before mapping.
- Non-dict top-level JSON hits `.get` -> AttributeError; the except
  must list it.
- Verified SDK fact: `@openuidev/react-ui` 0.17.0 `ThreadHeader`
  renders children in the header actions area beside built-in
  content; `fetchLLM` custom fetch gets `(url, init)` with an
  already-stringified JSON body, no Request object.
