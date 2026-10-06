# falsegreen vs falsegreen-js output formats differ

`post-write.sh` scans test files with `uvx falsegreen` (.py) and
`npx falsegreen-js` (.ts/.tsx/.js/.jsx). The two tools print
different text. Hook parsing must accept both.

- Clean, py: `No false-positive patterns found ...` (capital N).
- Clean, js: `... no false-positive patterns found.` (lowercase n).
- Finding, py: `path:line  [C5] msg` plus `Summary: N high, M low.`
- Finding, js: `HIGH C5   L1  msg` plus `N high, M low. <url>`.
  No brackets, no `Summary:` prefix.
- Exit code 20 = findings, 0 = clean, both tools.

Related gotcha: under `set -u`, a variable assigned only inside a
nested `case` branch aborts the script when expanded on a path the
branches skip. Initialize `fg=""` first.
