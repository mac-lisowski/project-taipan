# Railway deploys run from CI, not the GitHub app

Repo-connected services create a GitHub Deployment record per
deploy (railway-app[bot]); no opt-out exists and `checkSuites`
only controls check runs. Fix shipped: both services
disconnected via `railway service source disconnect` (repo:
null), and the `deploy` job in ci.yml runs
`railway up --service <name> --ci` after `ci-done` on push to
dev. `railway up` uploads the checkout and the service's
dockerfilePath still governs the build; verified end to end
with zero GitHub records. GitHub env `project-taipan / dev`
(branch policy: dev) holds secrets `RAILWAY_TOKEN` (project
token) + `RAILWAY_PROJECT_ID` and vars `RAILWAY_ENVIRONMENT`,
`RAILWAY_SERVICE_WEB`, `RAILWAY_SERVICE_API`; the `environment:`
key must stay literal so env-scoped values resolve. Service
names were renamed to `project-taipan-web-dev` /
`project-taipan-api-dev` (use service IDs in API calls, names
break). `watchPatterns` also filter `railway up` deploys and a
SKIPPED deploy hangs `--ci` forever: patterns cleared on api
(serviceInstanceUpdate), deploy job has timeout-minutes: 15.
