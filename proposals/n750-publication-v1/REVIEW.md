# Exact publication record — owner review pending

Selection PR #32 merged into `day4/additive-m2` at
`352bd4d203cfbcfb308cb03106bb18e0f98e6f7f`. The publisher from PRs #30/#31
is unchanged. `owner-record.proposed.json` binds the accepted selection plan,
five admission and four freeze output hashes, implementation and caller hashes.
`review.json` records the proposed and expected approved SHA-256 values.

The installer follows the existing trusted-terminal procedure: owner execution
changes only the existing OWNER_GRANT_PATH / OWNER_GRANT_SHA256 constants and
creates the approved successor record. It preserves the prior N450 record,
rejects unexpected implementation changes, and performs no publication itself.
The agent has NOT run this installer or created an approved record. Old local
grant SHA values are obsolete.

Before publication, resolve the requirement in `docs/cohort_publication.md`:
“Before actual publication, qualified remote RAW SHA/readback and the exact
owner-approved source selection must exist outside proposal text.” Retained
checksums cover 450 sources (5 Treasury, 445 SEC). The exact 300 SEC sources
lacking retained remote evidence are in `remote-evidence-unresolved.json`.
A successful read-only Databricks volume listing does not close this gap.
This is not a claim the objects are absent. No upload or RAW processing was done.
Supply existing checksum evidence for these identities, or make an explicit
owner decision on whether remote availability is a physical-admission requirement
versus a later processing prerequisite. No such decision has been fabricated.

Once prerequisites are resolved and the owner independently reviews the exact
record, the exact install command and expected approved SHA are in `review.json`.
After installation the existing publisher can be called using:

```sh
PYTHONPATH=src /Users/lightnino/Projects/edp-lab/.venv/bin/python scripts/publish_cohort.py proposals/n750-step1-v3/plan.json admission
PYTHONPATH=src /Users/lightnino/Projects/edp-lab/.venv/bin/python scripts/publish_cohort.py proposals/n750-step1-v3/plan.json freeze
```

Do not run publication until the above prerequisite is resolved. Independent
readback and historical seal verification still follow actual publication.
`C1500_COHORT_PASS` is not claimed. This package must not be merged as completed
Step 1 while approval or integrity prerequisites remain unresolved. No Step 2.
