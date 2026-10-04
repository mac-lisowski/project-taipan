# Railway deploys run from CI, not the GitHub app

Repo-connected services create a GitHub Deployment record per
deploy (railway-app[bot]); no opt-out exists and `checkSuites`
only controls check runs. Fix shipped: both services
disconnected via `railway service source disconnect` (repo:
null), and the `deploy` job in ci.yml runs
`railway up --service <name> --ci` after `ci-done` on push to
dev. `railway up` uploads the checkout and the service's
dockerfilePath still governs the build; verified end to end
with zero GitHub records. Requires secrets `RAILWAY_TOKEN`
(project token, dev env) and `RAILWAY_PROJECT_ID` on the
`project-taipan / dev` GitHub environment (branch policy: dev).
