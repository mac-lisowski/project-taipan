# Verify CI jobs locally with act

Run a job against the rootless daemon before claiming it passes:

```
DOCKER_HOST=unix:///run/user/1000/docker.sock act -j <job> \
  -W .github/workflows/ci.yml \
  -P ubuntu-latest=catthehacker/ubuntu:act-24.04 --pull=false
```

Install act if missing (github.com/nektos/act). Jobs that map
service ports (test-api -> 5432) conflict with any other project's
postgres already bound on the host.
