# Day 4 schema matching and identity candidate report

Agent `EDP_CANDIDATE_AGENT_V2_BOUNDED_V1` was scored on the [fixed 23 cases](../metadata/evaluations/agent_v2/ground_truth_v1.json), SHA-256 `9ba83190b260b1bb5ac7feb0043fa7591b9da846f49a40be0d7fe6c4428477fd`, fixed at commit `31fd869c697e3afd6611838794513a3fcf64e927`. [Step 10](../docs/day4_step10_agent_v2_quality_regression.md) and its [machine result](../metadata/evaluations/agent_v2/quality_regression_step10_v1.json) are authoritative; this is the eight-task report, not a new benchmark run.

| Actual label / predicted | MATCH | NON_MATCH | UNRESOLVED |
| --- | ---: | ---: | ---: |
| MATCH | 7 | 0 | 0 |
| NON_MATCH | 0 | 10 | 0 |
| UNRESOLVED | 0 | 0 | 6 |

STTM **11/11**, Crosswalk **4/4**, ER **8/8**, overall **23/23** against curated labels. There were zero observed false matches, false non-matches/splits or premature resolutions within the question-specific benchmark. Six ambiguity cases S08, S11, E05, E06, E11 and E12 remained unresolved. Eight proposals required review; three consequential requests (E05, E06, S08) were recorded, with zero responses or semantic approvals. The S09 correction added missing conflict evidence without changing its NON_MATCH label or other case results. No numerical confidence was emitted; unsupported canonical promotions observed: zero. A same-token MATCH is not a canonical entity match.

**NEW_CAPABILITY / NO_COMPARABLE_BASELINE**: earlier Agent V1 did not answer these same STTM/Crosswalk/ER questions. The contemporaneous name-only heuristic was 8/23, not an Agent V1 version comparison. The benchmark is curated engineering evidence, not blinded independent adjudication or production accuracy. Original [proposals](../metadata/evaluations/agent_v2/proposals_v1.json), [inputs](../metadata/evaluations/agent_v2/inputs_v1.json), [human review](../metadata/evaluations/agent_v2/human_review_v1.json) and [candidate ERD](../docs/agent_v2_candidate_erd.md) retain witnesses and limits. No business mapping or canonical identity was approved.
