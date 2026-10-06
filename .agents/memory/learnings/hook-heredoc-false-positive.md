# Heredoc payloads tripped pre-exec gates; fixed by whitelisted stripping

Symptom: `cat > f.md <<'EOF'` with `git commit` (or `DROP TABLE`)
in the payload was blocked - the flat match sees the payload as
command text.

Fix in pre-exec.sh: an awk pass strips heredoc BODIES before
cmd_flat is computed, but only for write sinks. Every segment
holding `<<` must be cat/tee; the line may not contain `|`,
backtick, `$(`, `eval`, or process substitution `>(`/`<(`.
`<<` inside quotes, after `#`, inside `${...}` spans, or as part
of `<<<` is not an opener. Delimiters must match
`[-._A-Za-z0-9]+` - a tag carrying metachars (e.g. `X}` pulled
from `${v:-w<<X}`) can never terminate and would hide unchecked
lines. Only `<<-` tolerates an indented terminator (per-tag flag);
plain `<<` requires column 0.

Why the whitelist: `bash <<EOF`, `x <<EOF | sh`,
`eval "$(cat <<EOF)"` all EXECUTE the body. Stripping those would
hide real commits - an evasion, not a fix. Round-2 review found
two more live bypasses the same way: `cat <<EOF > >(sh)` (process
substitution executes the body) and `cat ${v:-w<<FOO } > f`
(phantom tag never terminates -> rest of command stripped).

Residual false positive (accepted, documented in hooks README):
`git commit` inside a normal quoted string still blocks, e.g.
`echo 'run git commit after review'`. Do not strip quotes:
`git "commit"` is already a documented evasion and blanking quoted
text adds parser risk.

Battery: `/tmp` staging pattern - payloads must come from files,
never the exec command itself (hook-editing-lockout.md). The last
battery was /tmp/px-battery3.sh (36 cases); not committed.
