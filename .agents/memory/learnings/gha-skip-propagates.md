# Job skipped because an upstream needs job was skipped

GitHub propagates `skipped` down the whole needs chain: if any
job upstream in the dependency graph is skipped, a later job is
skipped even when its direct `needs` succeeded and its `if`
evaluates true (implicit success() check fails). Fix: prepend
`always() &&` to the job `if`, and check the direct need
explicitly, e.g.
`if: always() && ... && needs.ci-done.result == 'success'`.
Same pattern as the test jobs needing `changes` (which is
skipped on push). Ref: actions/runner#491.
