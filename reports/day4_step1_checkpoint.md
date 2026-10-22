# Day 4 Step 1 — recovered selection checkpoint

Status: **WAITING_FOR_OWNER_APPROVAL — selection recovered; publication not executed**.
This is not an admission, freeze or Step 1 completion marker.

PRs #30/#31 are merged into `day4/additive-m2`; their reusable publisher is reused
unchanged. Step 0 remains accepted; no baseline evaluation was repeated.

Recovered packet: [review](../proposals/n750-step1-v3/REVIEW.md),
[exact plan](../proposals/n750-step1-v3/plan.json),
[qualification](../proposals/n750-step1-v3/qualification.json),
[hash index](../proposals/n750-step1-v3/review-index.json).

750 mechanically qualified sources comprise 5 Treasury XML and 745 SEC Daily
Master; 269,323,425 bytes. Exact Universe membership, zero historical overlap,
41 excluded holdouts and baseline pins are checked by portable tests. The
production read-only planner validated the original pinned inventory and proposed
output hashes: 750 new registrations; 1,500 combined identities; 754 historical
manifest rows preserved and 750 appended (1,504 total).

Completed physical qualification was reused, not rerun. Retained remote SHA
readback covers 450 selected sources; the other 300 are not represented as remotely
verified. Required remote scope must be reconciled before publication. No RAW was
uploaded, parsed or processed. All original local edits remain preserved in their
original worktree; no competing publisher was copied.

Pending: final exact owner record/trusted installation, actual exclusive-create
admission and cohort freeze, complete publication readback and historical seal
comparison. Older local owner-record hashes are obsolete. Proposed output hashes
do not establish publication. No `C1500_COHORT_PASS` is claimed.

Step 2 NOT STARTED. Package PRs target the Day 4 integration branch; no main merge
before Step 14.
