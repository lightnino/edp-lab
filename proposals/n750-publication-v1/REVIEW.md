# Exact publication record — owner review pending

Selection PR #32 merged into `day4/additive-m2` at
`352bd4d203cfbcfb308cb03106bb18e0f98e6f7f`. PR #33 remains draft. The publisher
from PRs #30/#31 and the accepted 750-source selection remain unchanged.

## Explicit scope amendment

[Admission boundary amendment](admission-boundary-amendment.md) implements the
owner's clarification: Step 1 requires qualified local RAW identity/SHA/provenance,
Universe membership, disjointness, historical preservation and exact approved
metadata publication/readback. Remote availability/SHA verification is mandatory
before Step 8 processing. It is not a Step 1 publication prerequisite.

Remote evidence remains 450 VERIFIED / 300 UNVERIFIED, with no mismatches
established. The unchanged `remote-evidence-resolution.json` records the earlier
location search; its BLOCKED labels describe remote verification, not physical
admission validity. No remote PASS is inferred. Step 8 must not process unverified
sources. Remote mapping is handled separately; no further search is performed.

## Exact owner approval and installation

`owner-record.proposed.json` binds this amendment, exact plan, existing evidence,
implementation/caller hashes, five admission outputs and four freeze outputs.
`review.json` contains final proposed/expected-approved SHA-256 values and the
exact trusted installation command. All previous owner-record SHAs are obsolete.
The selected sources, plan and expected publication bytes have not changed.

The installer follows the existing trusted-terminal procedure: owner execution
changes only the existing OWNER_GRANT_PATH / OWNER_GRANT_SHA256 constants and
creates the approved successor record. It preserves the prior N450 record,
rejects unexpected implementation changes, and performs no publication itself.
The agent has NOT run it or created an approved record.

After explicit approval and trusted installation:

```sh
PYTHONPATH=src /Users/lightnino/Projects/edp-lab/.venv/bin/python scripts/publish_cohort.py proposals/n750-step1-v3/plan.json admission
PYTHONPATH=src /Users/lightnino/Projects/edp-lab/.venv/bin/python scripts/publish_cohort.py proposals/n750-step1-v3/plan.json freeze
```

Actual publication, independent exact readback and historical preservation checks
must precede `C1500_COHORT_PASS` and merging PR #33 into `day4/additive-m2`.
Step 2 is not started; no merge to main is authorized.
