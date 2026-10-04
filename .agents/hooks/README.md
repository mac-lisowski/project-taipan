# Agent hooks

Portable hook scripts, wired per tool. Scripts are tool-agnostic:
they read the hook JSON on stdin, parse with `jq`, and exit.

## Coverage

| Tool | Manifest | Notes |
|---|---|---|
| Claude Code | `.claude/settings.json` | Native. |
| Devin CLI | `.claude/settings.json` | Compat: Devin auto-reads `.claude` hooks (`read_config_from.claude`, default on). |
| Grok | `.claude/settings.json` | Compat. Needs `/hooks-trust` once per project. |
| ZCode | `.zcode/config.json` | Native. Needs `hooks.enabled: true` (set). |

Do NOT add `.devin/hooks.v1.json` while `.claude/settings.json`
defines hooks. Devin reads both, and every hook would fire twice.

## Scripts

| Script | Event | Action |
|---|---|---|
| `pre-exec.sh` | PreToolUse (`exec`/`Bash`) | Blocks bare `python`/`pytest`/`ruff`/`alembic`/`uvicorn` (use `uv run`), `pip` (use `uv add`), `.venv` activation, force push, `git reset --hard`, dangerous `rm -rf`, `DROP TABLE`. Then runs mode routing. |
| `pre-write.sh` | PreToolUse (write tools) | Blocks writes to `uv.lock`, `skills-lock.json`, `.venv/`, `.git/`. Then runs mode routing. |
| `post-write.sh` | PostToolUse (write tools) | Em-dash check; `ruff check` on `.py`; 300-LOC warning on source files; BFF-boundary warning on `apps/web/src` outside `app/api/`; `falsegreen`/`falsegreen-js` scan on test files + one-shot `test-smell-review` nudge. Then runs mode routing. Findings go to context. |
| `post-exec.sh` | PostToolUse (`exec`/`Bash`) | After `db-revision`: remind to review the migration. Then runs mode routing. |
| `session-start.sh` | SessionStart | Injects `.agents/memory/current.md`, the current activity mode, and the mode command; warns on broken skill symlinks. |
| `stop-nudge.sh` | Stop | Once per session: if tree is dirty and memory untouched, tells the agent to update memory. |

## Activity modes

The agent declares a fixed one-word label for its current phase:

```bash
bash .agents/hooks/agent-mode.sh set plan      # set
bash .agents/hooks/agent-mode.sh get           # get (prints "none" if unset)
bash .agents/hooks/agent-mode.sh clear         # clear
bash .agents/hooks/agent-mode.sh list          # vocabulary
```

Vocabulary: `plan implement test review debug docs commit`. `set`
rejects anything else. State is a file in `/tmp` keyed by project
root (an exec'd script cannot see `session_id`). `set` to a different
mode and `clear` reset all markers under this project's key - route
dedup and the one-shot test-scan nudge - so a new mode re-nudges once.
Re-setting the same mode is a no-op and keeps the markers.

`route.sh` is the dispatcher. Parent hooks call it last with the raw
hook JSON on stdin and the event name as `$1`. If a mode is set and
`.agents/hooks/hooks.d/<mode>/<event>.sh` exists, it runs it.

Route contract for `hooks.d/<mode>/<event>.sh`:

- env: `TAIPAN_MODE`, `TAIPAN_TARGET` (file_path, notebook_path, or
  command), `TAIPAN_ROOT`. Prefer `TAIPAN_TARGET` over re-parsing stdin.
- stdin: the hook JSON (usually unneeded once `TAIPAN_TARGET` is read).
- stdout: a short plain-text nudge. `route.sh` hands it to the
  parent hook, which wraps it in `additionalContext`.
- Each nudge fires **once per mode-set** (dedup marker in `/tmp`),
  and only when the route actually printed something.
- Never block: exit 0 always. Hard gates live in the parent scripts,
  not in mode routes. Mode is advisory on purpose: a label the agent
  forgot to set must not silently disable enforcement.
- Skipped inside subagents (hook input carries `agent_id`).

Add a mode route: create `hooks.d/<mode>/<event>.sh` with
`<event>` in `pre-exec post-exec pre-write post-write`. No manifest
edit needed; parent hooks already call `route.sh`.

## Contract

- stdin: `{"tool_name", "tool_input": {"command"|"file_path"|"notebook_path"}, "session_id", "agent_id"?}`.
  `agent_id` is present on subagent tool calls; `route.sh` skips them.
- Block: exit `2`, reason on stderr.
- Context: stdout `{"hookSpecificOutput": {"hookEventName": "<Event>", "additionalContext": "..."}}`.
- Stop nudge uses `{"decision": "block", "reason": "..."}` so the agent continues once.
- Project root: `$DEVIN_PROJECT_DIR`, then `$CLAUDE_PROJECT_DIR`, then
  the script location (`<root>/.agents/hooks/`), then cwd.
- Fail-open: a parse error exits 0. A broken hook must not halt the agent.

## Layout

```
.agents/hooks/
  mode-lib.sh     shared helpers (sourced, not run directly)
  agent-mode.sh   mode CLI the agent calls via exec
  route.sh        mode dispatcher, called by parent hooks
  hooks.d/        mode routes: hooks.d/<mode>/<event>.sh
    plan/pre-write.sh    warn once when editing code in plan mode
    review/pre-exec.sh   nudge code-review before commit in review mode
    test/pre-exec.sh     nudge the judgment pass before commit in test mode
```

## Test a script

```bash
echo '{"tool_name":"exec","tool_input":{"command":"pytest"},"session_id":"t"}' \
  | .agents/hooks/pre-exec.sh
echo $?   # expect 2

echo '{"tool_name":"exec","tool_input":{"command":"uv run pytest"},"session_id":"t"}' \
  | .agents/hooks/pre-exec.sh
echo $?   # expect 0
```

## See loaded hooks

- Devin CLI: `/hooks`
- Claude Code: `/hooks`
- Grok: `/hooks` (after `/hooks-trust`)
