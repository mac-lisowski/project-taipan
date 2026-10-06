# httpx2 silently retries requests that lose their response

- 2026-10-05, KMS test teardown: `delete_project` raised 404 although
  the delete succeeded. Infisical logs showed two DELETEs 9ms apart.
- Cause: a burst of HTTP-500 responses (garbage-decrypt tests) drops
  a keep-alive connection; httpx2 retries the in-flight DELETE on a
  fresh connection. The first attempt already deleted the project,
  so the retry gets 404.
- How to apply: do not assume one request equals one wire call with
  httpx2. For idempotent operations (DELETE), treat a 404 after a
  prior success as done, not as failure. Test fixtures that clean up
  should tolerate this case narrowly.
