# Shared model catalog

- One module-scoped `ModelCatalog` backs `GET /chat/models` and the
  `/chat/complete` validator, so the picker and the 422 can never
  disagree on the allowed set.
- Only a successful fetch moves `_fetched_at`; a failed refresh keeps
  the last list and retries next call. Cold failure serves the
  configured `chat_model` alone.
- Response shape `[{id, name, default?}]`: `default: true` marks (or
  appends) `chat_model` so the web learns the API default without a
  second source.
- The web sends the model via a custom `fetch` passed to `fetchLLM`
  that rewrites `init.body` per request; rebuilding the ChatLLM would
  reset SDK stream state.
