# Evals

Evaluation task specs for the in-repo agent. Layout convention:

```
evals/<suite>/tasks/<task-id>/Task.md
```

`Task.md` is the control-plane spec; it is hidden from the agent under
test. A task is runnable once it has a `task.toml` and a target app
(e.g. `apps/agent`, planned).

The process lives in `.agents/skills/eval-engineering/SKILL.md`.
