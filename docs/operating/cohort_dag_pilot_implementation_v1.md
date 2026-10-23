# Cohort DAG pilot implementation — execution contract and readiness

**Status: IMPLEMENTATION PR — guarded orchestration milestone, not a certified live C2000 run.**

This adds a deterministic plan compiler on top of PR #51's existing signed queue runner and connects the project-only PR #54 C3.4 numbers. It does not mutate accepted C1500, approved Universe, or run N500 processing. It cannot be interpreted as proof of autonomous end-to-end readiness until all external adapters exist.

## Where the pieces fit

- **Input/authority:** Universe approval and separate Cohort admission remain independent; acquisition candidate staging grants neither. P1 selects the exact N roster. P5 asks the protected 0A authority to evaluate it under the standing policy; only a new semantic or policy decision returns to the owner.
- **Planning:** `edp_lab.operating.dag` compiles a versioned `EDP_COHORT_DAG_PLAN_V1` into a deterministic `EDP_QUEUE_V1` that PR #51's runner can execute. Selected `route` is `INITIAL_MODEL`, `CORPUS_ONLY`, `ADDITIVE` or `CORRECTIVE`; `UNRESOLVED` cannot be promoted as a model route.
- **DAG sequence:** P0 baseline → P1 selection → P2 observation → P3 B1 route evidence → P4 branch contract → P5 bounded authorization evidence → P6 cohort input freeze → P7 smoke → P8 provisional RAW/CLEAN/QUERYABLE processing evidence → P9 applicable controls + Lossless stage evidence → P10 A/B2/C Stability evidence → P12 signed C3.4 checks + operating evidence → P13 independently signed live freeze. P11 is **conditional recovery**, implemented by PR #51's bounded queue resume; P14 Git is **separate guarded closeout** under PR #51 Git adapter, not falsely counted as part of a post-freeze Databricks receipt.
- **Work/execution distinction:** `stage_gate` validates *externally produced and independently signed LIVE stage evidence* keyed by cohort/output/stage/**exact queue hash**. It **does not perform** the claimed Databricks operation. Optional `local_tasks` for P2/P4/P7 run pinned Codex prompts under PR #51's restricted local Codex task. An optional **`guarded_create_table` at P8** invokes the existing #51 signed, ledgered, single-`CREATE TABLE` adapter and waits for a separately verified exact-operation remote readback before P8 may complete. It does **not** yet implement arbitrary Day 5 RAW→CLEAN→QUERYABLE processing or guarded Delta view publication. **Real P1/P6/full-P8/P13 executors and independent verifier integration remain blockers**.
- **Test and budget:** P9 auto-selects existing registry controls from source-family tags, and forces `RAW` tag (FSDS automatically adds FIN, Treasury adds TRY); this is not yet a complete source-field applicability inventory. P12 selects exact phase reference in `metadata/operating/edp_lab_pilot_c3_4_budget_v1.json` pinned by the signed grant. An independent timing receipt supplies exact source/output/phase/method, policy hash, live measurement digest and comparability. ≤5× PASS; 5×<t≤10× technical PASS + nonblocking visible WARNING; >10× BLOCKED, sticky `NEEDS_HUMAN_DECISION`. Missing phase/method/unapproved proof cannot be reported PASS.
- **Independent freeze:** P13 calls the unchanged PR #51 `freeze_verify` gate, requiring a separately signed exact-output LIVE receipt with verified Delta IDs/history/properties, row counts, source lineage, QUERYABLE versions and live readback, not a Git JSON status marker.
- **Simulation:** `simulation_only: true` compiles dry-run receipt placeholders for test/demo. Such queues are permanently **rejected** if run without `--dry-run`. A simulated complete DAG is not an accepted output.
- **Resume:** PR #51 checkpoint/recovery persists COMPLETE status; uncertain external writes remain VALIDATING until signed independent readback. A blocked budget/integrity result is sticky, cannot be cleared by restarting the same signed queue.

## How to compile (without granting execution authority)

Prepare a JSON plan with these required keys:

```json
{
  "schema": "EDP_COHORT_DAG_PLAN_V1",
  "cohort": "C2000",
  "output": "workspace.edp_lab.o_c2000_candidate_v1",
  "route": "CORPUS_ONLY",
  "tags": ["RAW"],
  "source_families": ["FSDS", "TREASURY"],
  "contracts": {
    "parser": {"version": "<exact version>", "path": "<tracked file>"},
    "model": {"version": "<exact version>", "path": "<tracked file>"},
    "rule": {"version": "<exact version>", "path": "<tracked file>"},
    "registry": {"version": "V1", "path": "metadata/operating/validation_registry_v1.json"},
    "budget_policy": {"version": "V1", "path": "metadata/operating/edp_lab_pilot_c3_4_budget_v1.json"}
  },
  "stage_receipts": {
    "P0": "<signed external P0 evidence path>",
    "P1": "<P1>", "P2": "<P2>", "P3": "<P3>",
    "P4": "<P4>", "P6": "<P6>",
    "P7": "<P7>", "P8": "<P8>", "P9": "<P9>",
    "P10": "<P10>", "P12": "<P12>"
  },
  "budget_phases": [
    {"phase_id": "sql_table_creation", "receipt": "<signed live timing>"}
  ],
  "control_receipts": {},
  "freeze_receipt": "<signed independent live result freeze>"
}
```

**Optional bounded P8 CREATE TABLE action:** the plan may additionally contain `"guarded_create_table": {"operation_id": "<unique>", "databricks_path": "<owner-approved exact path>", "databricks_table": "<approved table>", "statement_path": "<in-repo pinned JSON statement>", "external_receipt": "<signed exact-operation live readback>"}`, and a matching `contracts.statement` hash/version pin. This uses PR #51's exclusive CREATE TABLE boundary and durable reservation; it is **not** a general-purpose processing adapter or permission to run raw Databricks CLI scripts. The source must be an approved member of the cohort grant, and actual execution requires an independent protected runtime with credentials and a signed readback receipt. No execution is performed by compiling the plan.

**The example is a schema illustration, not an approved C2000 route or actual cohort.** B1 classification must be supported by real N500 observations and any required semantic decision. For standing-policy execution the plan also supplies `previous_cohort`, `prior_receipt` (independently signed live prior-membership evidence) and `sources` (exact P1 identity/path/SHA triples). P5 checks these against the signed 0A policy and approved Universe; the broker-signed exact grant is its receipt, so `stage_receipts.P5` is omitted. Source-specific validation must be completely inventoried rather than assuming all of C2000 consists only of FSDS/Treasury.

From repository root:

```sh
uv run python -m edp_lab.operating.dag my-reviewed-plan.json runs/operating/c2000-queue.json
```

The runner demands a queue located **inside the repository** to verify its hash-pinned relative path. Compile there (e.g. `runs/operating/c2000-queue.json`). The protected policy broker checks the resulting exact bytes and signs the run grant automatically. Live receipts remain separately verified. Do not put signing keys in the repository or an agent-editable worktree.

```sh
# Once the independent 0A broker and protected runtime are installed:
EDP_OWNER_TRUST_DIR=/owner/trust EDP_POLICY_BROKER_SOCKET=/owner/broker.sock \
  uv run python -m edp_lab.operating.runner \
  runs/operating/c2000-queue.json auto runs/operating/c2000 --dry-run
```

For an explicit simulation, set `simulation_only: true` in the plan before compiling; this is separately hash-pinned and cannot be promoted into a live queue. A *non-simulation* plan requires real stage receipts and independently approved authority before it can advance.

## Required before real autonomous N500 → C2000

1. Implement the guarded N500 source selection, admission/input freeze and RAW→CLEAN→QUERYABLE adapters, using **exact existing source code/Databricks version pins** and external secrets. Scripts that bypass the protected write boundary cannot be treated as Agent-authorized.
2. Implement native, owner-independent stage/readback receipt production (the test harness signs throwaway fixture documents; this is not deployed trusted verification).
3. Tie B1 classification and the per-family/field applicability inventory to observed N500 evidence and the correct model route; fill missing economic-rule conditional research/approval/registration where required.
4. Enforce project-specific grant limits separately from the C3.4 observed performance acceptance thresholds; don't use 10× as permission to exceed a job timeout.
5. Extend secured writes to non-CREATE TABLE Databricks processing/zero-copy final view and the guarded post-freeze Git CI/merge closeout.
6. Run real, bounded integration and negative authorization tests in Databricks and verify exact remote Delta/UC and SQL readbacks. Until then, no `AUTONOMOUS_END_TO_END_PASS`, no C2000 freeze and no assertion of a live agent deployment.

## Local tests

```sh
uv run pytest -q tests/operating/
uv run ruff check src/edp_lab/operating tests/operating/
```

The tests exercise exact 5×/10× boundaries, tampered timing policy, forged signed timing receipts, changed source/tag control applicability, DAG task order and complete predecessor dependencies, signed runner warning/hold/resume, and simulated-only rejection.
