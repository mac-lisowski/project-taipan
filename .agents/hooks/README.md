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
| `pre-exec.sh` | PreToolUse (`exec`/`Bash`) | Blocks bare `python`/`pytest`/`ruff`/`alembic`/`uvicorn` (use `uv run`), `pip` (use `uv add`), `.venv` activation, force push, `git reset --hard`, dangerous `rm -rf`, `DROP TABLE`. |
| `pre-write.sh` | PreToolUse (write tools) | Blocks writes to `uv.lock`, `skills-lock.json`, `.venv/`, `.git/`. |
| `post-write.sh` | PostToolUse (write tools) | Em-dash check + `ruff check` on `.py` files. Findings go to context. |
| `post-exec.sh` | PostToolUse (`exec`/`Bash`) | After `db-revision`: remind to review the migration. |
| `session-start.sh` | SessionStart | Injects `.agents/memory/current.md`; warns on broken skill symlinks. |
| `stop-nudge.sh` | Stop | Once per session: if tree is dirty and memory untouched, tells the agent to update memory. |

## Contract

- stdin: `{"tool_name", "tool_input": {"command"|"file_path"}, "session_id"}`
- Block: exit `2`, reason on stderr.
- Context: stdout `{"hookSpecificOutput": {"hookEventName": "<Event>", "additionalContext": "..."}}`.
- Stop nudge uses `{"decision": "block", "reason": "..."}` so the agent continues once.
- Project root: `$DEVIN_PROJECT_DIR`, then `$CLAUDE_PROJECT_DIR`, then cwd.
- Fail-open: a parse error exits 0. A broken hook must not halt the agent.

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
