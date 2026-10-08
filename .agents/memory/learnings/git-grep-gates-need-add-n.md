# git-grep gates need `git add -N` on new files

- `scripts/check-unreached-components.sh` and `check-file-size.sh`
  scan via `git grep` / `git ls-files`: the index, not the disk.
- A brand-new untracked component fails "no importer" even when wired,
  because the importer file itself is invisible to git grep.
- Fix: `git add -N apps/web/src` (intent-to-add). Registers paths
  without staging content; no commit needed.
- `check-bff.sh` already scans untracked files on disk explicitly.
