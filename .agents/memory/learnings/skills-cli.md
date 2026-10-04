# npx skills CLI behavior in this repo

`npx skills add <owner/repo@skill>` installs real files into
`.agents/skills/<name>/` and symlinks into `.claude/skills`,
`.devin/skills`, `.grok/skills`, `.zcode/skills`. Both the files and
the symlinks are committed (see `skills-lock.json`).

Gotchas:

- `-a '*'` also writes a stray `agent/skills/<name>/` copy at repo
  root (an agent literally named "agent"). Delete it after install.
- Editing an installed skill diverges from upstream. `npx skills
  update` will clobber local edits. We trimmed botica-internal
  references out of `test-smell-review` (their `agent_config.py`,
  CES rules, issue links). Reapply the trim if updated.
