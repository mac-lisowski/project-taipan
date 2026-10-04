# Diff hash must bind worktree content, not diff position

`taipan_diff_hash` backs the commit-review marker. First version
hashed `git diff --cached` + `git diff` + untracked paths. Two
failures:

- `git add` after stamping moved the same bytes between sections,
  changing the digest and forcing a re-stamp on the normal
  review -> stage -> commit flow.
- Untracked files contributed only their paths; content edits after
  stamping kept the marker valid.

Fix: hash `path<TAB>worktree-blob-hash` per path from
`git status --porcelain -z --untracked-files=all`, sorted
(`LC_ALL=C sort`). `git add` reorders status output and flips the XY
columns, so sort by path and drop the status letters from the record.
Staged content that diverges from the worktree (partial staging)
still contributes its `git diff --cached` for that path: a stamp
cannot bless an unreviewed staged version, at the price of
invalidating when re-staging a partially staged path.
