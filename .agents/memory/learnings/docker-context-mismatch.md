# docker build apps/web tested a different context

`docker build apps/web` uses `apps/web` as context, NOT the repo
root - it proved nothing about the documented
`docker build -f apps/web/Dockerfile .` and the mismatch shipped
broken. Verify the exact command being documented/deployed.
