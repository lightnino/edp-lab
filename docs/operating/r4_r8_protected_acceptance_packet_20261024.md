# R4 and R8 protected acceptance packet — PR #66

**Scope:** prepare a disposable protected fixture and read-only installed-CLI
inspection. No historical Day 5 Queue, Supervisor, checkpoint, ledger, signed
grant or recovery installer is an acceptance fixture. PR #61 is untouched.

## R4 owner review before any protected installation

The owner reviews the exact PR HEAD/source hashes, chooses a **new disposable**
protected fixture state path, pinned runtime path, separate launchd label,
operator identity, notifier executable/arguments and alert thresholds. Render
the [launchd template](r4_watchdog_launchd.plist.template) and [private config
template](r4_watchdog_config.json.template) only after review. Install the
config as owner-controlled mode 0600, the fixture state files and alert as
0600, and deny group/world write on their parent directories. The notifier
must be independently controlled, with a tested route to the designated
operator. The Watchdog is scheduled independently every 30 seconds. Neither
template is an installed service or authority to alter the historical
`org.edp-lab.day5-supervisor` service.

Prepared artifact SHA-256 pins: `supervisor_health.py`
`ff8cc7a6c130229b485fc6be370710f751234e5f1cb4355e91f6edcf589c4ab6`,
`watchdog_delivery_r4.py`
`a0729374421a242473c4ad83bcbc22627378b15f50f9c6a2a50078648b2c7e83`,
launchd template
`5aaaebf8bb5a141b1329f3a5c88435e16979df547d4416e536016c96617c242f`,
and config template
`fc3bb9ec9a01b702aa0ca51bebfbb14cbfaf2e80bf048efa18fb04409144bd94`.

The protected acceptance harness must use a disposable signed/no-write Queue
and isolated ledger/checkpoint. Record hashes of these before and after each
case. Do not supply Databricks write credentials to this fixture. Test normal
terminal completion, nontransient `Denied` including missing Statement ID,
unexpected exception, `SIGKILL`, live hung worker with expired heartbeat,
live process with fresh heartbeat but no progress, launchd restart/backoff,
Watchdog check failure, notifier success/failure and read-only sanitized status.
Capture protected launchd, stdout/stderr, notifier receipt, status and file
permission evidence with an independent owner-controlled recorder. Compare
source files, checkpoint, ledger, Queue and external operation counts before
and after; the count must remain zero for this fixture. Any automatic SQL
replay or protected-state mutation fails acceptance.

**Current gate:** R4 offline tests PASS. Protected-host installation,
independent schedule, actual operator alert and launchd restart/backoff are
**BLOCKED pending final Owner execution approval and execution**. The Owner
approved the bounded disposable-fixture scope, then required exact paths,
commands, service configuration and notification route before installation.
The [review packet](r4_fixture_review/owner_execution_packet.md) supplies
those artifacts. The fixture notifier test sends to a disposable local inbox
only; it is not delivery to the designated operator.

## R8 installed-CLI evidence and limits

The local installed CLI path is `/opt/homebrew/bin/databricks`, version
`1.21.0`, binary SHA-256
`00b2b4513660ea587ee5350b5030d6351d17cc326ca69fce4c60fdf9e538f303`.
The reviewed R8 parser source SHA-256 is
`2c9c268b111705236845be930587f8d2dde5882e08239fc2e8b3e85407f777e3`.
The explicitly selected `edp-lab` profile was valid, and authenticated
`current-user me` returned the expected principal. The read-only smoke used
`PRESENT` for `workspace.edp_lab.n500_input_roster_day5_v1` and the bounded
2026-10-23 21:30–22:00 UTC Query History window. It returned one complete
empty history page and an exact matching UC table identity. The sanitized
result reports schema `EDP_READONLY_CLI_PREFLIGHT_V2`, `pages_checked=1`,
`visible_queries=0`, `observed_uc_state=PRESENT`, and
`uncertain_external_effects_resolved=false`. Identity response SHA-256:
`c1d53d2b0605eb92d7864c45fdc663aebac93a875ddd49dcfe6b0abf3445c4d1`;
History response SHA-256:
`9fc9149be12779da64a26415b20b2f09a314d6faa817cb33a86a25b627a4053a`;
UC response SHA-256:
`b02b593a457c66f37d686e686c33e99a75a9e13a5091194e0b31631203263349`.
Raw responses were consumed in process memory and **were not persisted in the
agent worktree**. These hashes bind the sanitized findings but do not replace
protected raw response retention by the owner.
The preflight now accepts `--protected-evidence-dir` and will write each raw
stdout/stderr once with mode 0600 only when that existing directory is
root-owned, owner-only and outside the worktree. It rejects an agent-owned
directory. The owner must supply the approved protected path in its terminal;
the local smoke deliberately did not use one.

R8 fixture tests cover text/JSON target absence errors, successful exact
presence, authentication failure, mismatched identity, pagination and
incomplete history. The current local CLI smoke is **PASS for read-only
connectivity and PRESENT format**. The actual protected Owner-terminal
identity/profile, owner-controlled raw response retention and protected
negative-response capture remain **BLOCKED pending owner execution**. Empty
history and target absence never imply `NO_REMOTE_EFFECT` or authorize a write.

## Acceptance decisions

| Gate | Current state |
| --- | --- |
| R4 offline deterministic/process fixtures | PASS |
| R4 protected schedule, restart/backoff, permissions, actual operator alert | BLOCKED — owner installation and evidence required |
| R8 offline parser and negative formats | PASS |
| R8 local installed CLI read-only PRESENT smoke | PASS — scoped to this user session/profile |
| R8 protected Owner-terminal preflight and protected raw response retention | BLOCKED — owner execution required |
| Incident R4/R8 overall closure | BLOCKED |

No PR #66 merge or historical recovery operation is authorized by this packet.
