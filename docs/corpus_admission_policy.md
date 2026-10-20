# C300 admission policy V1 — proposed for Human Review

Specification only. No source admission, cohort creation or population is performed.
Reuse [Source Identity](source_instance_identity.md), the pinned twelve-column
`metadata/corpus_manifest.csv` and single-column cohort roster format used by
`metadata/cohorts/GOLD_V2.csv`. Do not alter frozen records or introduce business keys.

An eligible member is one evidenced immutable physical delivery, assigned an unused
`SRC######`, with a distinct immutable RAW path, source family, exact SHA-256,
actual admission UTC recording, introduction cohort and explicit admission authority.
Archive members and rows are not additional instances. Reuse existing admitted IDs
when referencing their same deliveries in another cohort; never count them twice.
A changed delivery requires a new path and ID. Equal bytes alone neither establish
independent deliveries nor justify merging identities.

Before admission, retain publisher/channel, receipt/retrieval evidence, snapshot or
edition reference where available, and evidence locators with versions/hashes.
Record unknown historical acquisition details as unknown; do not manufacture them.
A present-day reviewer must explicitly disposition missing evidence for any proposed
C300 membership, including reuse of historical GOLD sources. Preserve that decision
outside frozen historical rows. Admission time is not acquisition time.

REAL instances require independently evidenced deliveries, with blank variant and
parent fields. CONTROLLED instances require documented manipulation/version,
existing parent ID, acyclic lineage, separate immutable bytes/path/hash/ID and
reproducible generation evidence. They never count as independent REAL deliveries.
Freeze any independently defined truth before evaluation; FALSE remains appropriate
when truth evidence is absent. A manipulation description alone is not ground truth.
Report total, REAL and CONTROLLED counts separately; no quota or mixture is inferred.

Freeze requires a reviewed roster of exactly 300 distinct eligible physical IDs,
verified hashes and retrievable provenance, recorded REAL/CONTROLLED composition,
review disposition of equal-hash deliveries and evidence gaps, and a versioned
membership/evidence snapshot with content hashes and actual freeze authority.
Verify RAW hashes before ingestion and member hashes before parsing. Preserve
historical cohorts, all prior membership, IDs, hashes, truth and outputs across
future nested expansion (evaluation SC1–SC6). A mismatch stops dependent work;
never repair by replacement, dropping a member or editing its frozen hash.

Maintain candidate evidence and explicit rejected/unresolved dispositions separately
from the admitted manifest and frozen roster. Use existing Decision Log statuses
and Finding Schema v1 where appropriate, without adding admission statuses to the
pinned manifest. Rejected/unresolved candidates do not count toward 300; retain
reason, evidence, review trigger and actual authority. No automatic replacement of
frozen members is permitted. Preserve all retained source bytes.

Physical admission, parser eligibility, profiling completion and semantic promotion
are independent. Admission does not require a successful business mapping, nor
imply profiling PASS. A source with blocked parsing can retain admitted immutable
identity while dependent profiling is blocked. Future snapshots need scoped parser
review; the approved GOLD_V2 lexical scope does not transfer automatically.
Semantic onboarding later uses evaluation SC7; it is not decided here.

Human Review question: accept this minimum admission policy, including explicit
review of historical provenance gaps, or require additional acquisition evidence
before eligibility? Acceptance permits future reviewed admission; the alternative
holds candidates with missing evidence. Neither option creates C300 now.
