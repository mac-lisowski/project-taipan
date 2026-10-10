# Model capability flags from /model/info

- `ModelCatalog._fetch` fetches `/v1/models` then `/model/info` on the
  same client, bearer, and TTL window; the info map caches beside the
  listing, keyed by `model_name`.
- Fail closed on info, never on listing: a failed or malformed info
  call yields an empty info map, so flags read false and unknown modes
  list. A failed info *refetch* therefore re-lists a previously
  filtered non-chat deployment for one TTL window.
- `mode` absent or null counts as chat; only a non-chat mode string
  filters. `/v1/models` stays the listing source, so info-only entries
  never list.
- Entries carry `vision`, `pdf_input`, `function_calling`,
  `tool_choice` (mapped from `supports_*`, `bool()` over null/absent).
  `supports_audio_input` is read by the payload but not exposed yet.
- `capabilities(model_id)` warms the cache via `list()` and answers
  all-false for unknown ids; it is the seam for attachment resolution
  and artifacts tool gating.
- Web `ChatModel` gained only the two attach-relevant flags as optional
  booleans; `isChatModelList` already tolerates extra keys.
