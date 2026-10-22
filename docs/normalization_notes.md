# Normalization notes — Day 3

Scope: explain relational design against actual Day 3 evidence without choosing
business keys or transforming M1. The accepted model remains `M1_LEXICAL_V1`.
Observed examples cite [B1](n450_b1_assessment.md),
[Stability V2](c750_stability_v2_evaluation.md) and the
[FD regression report](../reports/c300_fd_regression.md). Conditional examples below
are design illustrations, not executed experiments or approved source semantics.

## 1. Key taxonomy

A **superkey** uniquely identifies a tuple; a **candidate key** is a minimal
superkey. A **primary key** is the selected candidate key; other candidates are
alternate keys. Composite keys contain multiple attributes. A **foreign key**
requires a matching referenced key. A generated surrogate identifies stored rows
but does not establish the business identity of the thing represented. A business
key requires an approved domain meaning and scope, not just observed uniqueness.

Day 3 preserves source-instance IDs, binding fingerprints, original run IDs and
line/byte locators. These are technical references, not issuer/security keys.
Source-line uniqueness is scoped to the binding/run; field ordinals further locate
individual field occurrences. Exact native readback verifies these references.
It does not declare that CIK, Company Name or File Name is a canonical enterprise
key. Even all five N450 values together are not an occurrence identifier: actual
native verification retained 29,305 excess equal-looking occurrences. No source
occurrence is collapsed to enforce a supposed natural key.

## 2. Functional Dependencies

An FD `X → Y` means every pair of tuples agreeing on X also agrees on Y, under
the declared equality, population and NULL policy. It is a constraint over legal
states, not a conclusion from names or a few matching rows. A snapshot check can
find a counterexample or establish agreement within that snapshot; it cannot by
itself approve a permanent business rule. Keys, FDs, inclusion dependencies and
duplicate counts are different checks.

No general Day 3 FD discovery/validation experiment ran. N450 statistical results
cover three full selected tables, not a corpus-wide FD search. For example,
SRC010001 has 4,997 rows but only 3,096 distinct literal CIK values: CIK is not
unique in that table. This does **not** test or refute `CIK → Company Name`.
That FD remains untested; source NULL interpretation and business keys remain
unresolved. There is no FD confidence percentage or business confirmation.

## 3. Update, insert and delete anomalies

Conditional illustration: if a reviewed rule established one company name per
issuer at a defined time, repeating that fact on every filing row could cause an
update anomaly (only some copies changed), an insert anomaly (no place for the
issuer until a filing exists) or a delete anomaly (deleting its last filing also
removes its only stored name). Day 3 has not established that rule, time scope or
entity mapping, so these are possible design anomalies, not observed source errors.

Actual repeated N450 rows are preserved source occurrences. Updating names,
inserting inferred entities or deleting duplicates to resolve an illustrative
anomaly would exceed this experiment. RAW is immutable; any later approved
normalized representation must remain derived and retain lineage.

## 4. First Normal Form (1NF)

Classical 1NF uses scalar attribute values without repeating groups in the chosen
relational domain. A delimited five-column filing row can be represented with
scalar TEXT values; the meaning or internal structure of those strings is a
separate domain question. A literal delimiter inside approved field boundaries
does not license an additional semantic split.

M1's record table deliberately stores an ordered ARRAY of field STRUCTs and
preserves framing as well as DATA records. It is not certified as a classical
flat 1NF business relation. Its existing fields view exposes scalar field values
with source/run/binding/locator/ordinal references. This projection is useful for
queries but does not make a normalized issuer/filing model or justify deduplication.

## 5. Second Normal Form (2NF)

A relation is in 2NF when it is in 1NF and every non-prime attribute depends on
the whole of every candidate key, with no partial dependency on a proper subset.
Prime means appearing in some candidate key. A single chosen surrogate primary
key does not remove partial dependencies involving other candidate keys.

Conditional illustration: if a reviewed filing key were composite and a separately
reviewed issuer-name fact depended only on its issuer component, storing both in
one relation could violate 2NF. No such key or FD was approved for N450. Source
names and dates remain lexical strings; no 2NF status is asserted for the business
domain or M1's nested physical representation.

## 6. Third Normal Form (3NF)

For every nontrivial FD `X → A`, 3NF requires X to be a superkey or A to be prime.
This formal condition is more precise than simply banning every apparent chain
of dependencies. A reviewed decomposition may separate facts about different
determinants to avoid transitive redundancy.

Day 3 does not establish that CIK determines a time-invariant name, that a name
determines an issuer, or that File Name determines a business filing event. Thus
no issuer/name lookup table or 3NF certification is delivered. Technical binding
metadata is already separate from record occurrences, but this alone is not a
proof of domain 3NF.

## 7. Boyce–Codd Normal Form (BCNF)

BCNF requires the determinant of every nontrivial FD to be a superkey. Unlike
3NF it has no prime-attribute exception. Deciding BCNF requires an established
relation, complete relevant dependency assumptions and candidate-key reasoning.
A BCNF decomposition can lose local dependency preservation even while being
lossless. Neither the FDs nor a normalized business schema exist in this scope,
so BCNF evaluation and implementation are DEFERRED.

## 8. Lossless Decomposition

Classical lossless decomposition means joining the projections reconstructs the
original relation without spurious tuples. Under FDs, a binary decomposition is
lossless when its common attributes determine one of the two components. Bag
multiplicity and occurrence identity need additional care in a source-preserving
system; joining equal values can multiply rows or collapse distinct occurrences.

The experiment's Lossless 1–6 contract is broader and distinct from that theorem:
it tests accounting, fields, exact lexical multiplicity, RAW integrity, provenance
and applicable economic reconciliation. C750's 108 full-schema bidirectional
multiset checks and FIN regressions PASS under the versioned acceptance rules.
These prove the tested M1 views and snapshots, not a new normalized schema's join
decomposition. Future decomposition would need its own approved keys/FDs and
source/locator-aware reconstruction proof. No decomposition was executed here.

## 9. Dependency Preservation

A decomposition is dependency preserving when the dependencies projected onto its
components together imply the original dependency set, permitting enforcement
without joining the components. Losslessness does not guarantee this property;
standard 3NF synthesis can target both under a declared FD set, whereas BCNF may
require a tradeoff. SQL UNIQUE/foreign-key constraints also have SQL NULL and
multiplicity semantics that must match the reviewed rule.

No source-business FD set has been established, so dependency preservation is
NOT_IMPLEMENTED for an enterprise normalized model. Existing hash, namespace,
locator and FIN checks remain explicit operational/scoped invariants, not a
substitute for a dependency-preservation proof. No missing FD result is called PASS.

## 10. Normalization and cross-source semantic integration

Normalization organizes facts given agreed attributes, identities, keys and
dependencies. It cannot decide whether two publisher IDs denote the same issuer,
whether an amendment supersedes a filing, how reporting dates align, what a NULL
means, or which grain/unit/tolerance is correct. Equal names or tickers cannot
authorize a merge. Those decisions require evidence and human-approved policy.

Actual C2 controls preserve disjoint source namespaces and reject false merges,
duplicate collapse, fanout and locator drift; mandatory FIN regression covers
three fixed financial contexts. This supports **M1 source-preserving PASS**.
Enterprise semantic integration remains **NOT_IMPLEMENTED**. A normalized mini
schema is deferred because this experiment neither requires nor authorizes the
missing semantic choices. No M1 change, historical replay or output freeze occurs.
