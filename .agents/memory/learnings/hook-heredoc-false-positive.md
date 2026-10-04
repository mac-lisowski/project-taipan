# Heredoc payloads tripped pre-exec gates; fixed by whitelisted stripping

Symptom: `cat > f.md <<'EOF'` with `git commit` (or `DROP TABLE`)
in the payload was blocked - the flat match sees the payload as
command text.

Fix in pre-exec.sh: an awk pass strips heredoc BODIES before
cmd_flat is computed, but only for write sinks. Every segment
holding `<<` must be cat/tee; the line may not contain `|`,
backtick, `$(`, or `eval`. `<<` inside quotes or after `#` is not
an opener. Tag extraction strips quote chars and handles mid-word
quoting; terminators allow leading whitespace (early close only
re-checks more text, safe direction).

Why the whitelist: `bash <<EOF`, `x <<EOF | sh`,
`eval "$(cat <<EOF)"` all EXECUTE the body. Stripping those would
hide real commits - an evasion, not a fix.

Residual false positive (accepted, documented in hooks README):
`git commit` inside a normal quoted string still blocks, e.g.
`echo 'run git commit after review'`. Do not strip quotes:
`git "commit"` is already a documented evasion and blanking quoted
text adds parser risk.

Battery: `/tmp` staging pattern - payloads must come from files,
never the exec command itself (hook-editing-lockout.md). The last
battery was /tmp/px-battery2.sh; not committed.
