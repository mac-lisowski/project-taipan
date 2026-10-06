# Quality gates: LOC cap + BFF boundary

Hard file cap is 300 LOC (scripts/check-file-size.sh) and the BFF
boundary is scripts/check-bff.sh; both run in pre-commit and the
CI lint job. Exemptions only in the scripts, with a reason.
