# PR #66 R4/R8 protected execution review packet

**Status: prepared for final Owner approval; every privileged command below is
unexecuted.** The 2026-10-24 bounded scope approval permits preparation and
offline validation. It expressly requires this exact path/command/service/
notification review before protected installation. No historical Day 5
Supervisor, Queue, grant, credential or ledger is a test fixture.

## Exact protected paths and identities

| Purpose | Exact path or label | Proposed mode |
| --- | --- | --- |
| Isolated fixture root | `/private/var/db/edp-lab-r4-fixture-20261024` | root:wheel 0700 |
| No-write Queue | `.../queue/no_write_queue.json` | root:wheel 0600 |
| Empty fixture ledger | `.../ledger/operations.json` | root:wheel 0600 |
| Disposable checkpoint/status/alert | `.../state/` | dir 0700; files 0600 |
| Independent logs | `.../logs/` | dir 0700; files 0600 |
| Reviewed runtime copy | `.../runtime/src/` and `.../runtime/scripts/` | root-owned; dirs 0755, source 0644 |
| Watchdog config | `.../config/watchdog.json` | root:wheel 0600 |
| Watchdog launchd service | `/Library/LaunchDaemons/org.edp-lab.r4-watchdog-fixture.plist` | root:wheel 0644 |
| No-write worker restart fixture | `/Library/LaunchDaemons/org.edp-lab.r4-worker-fixture.plist` | root:wheel 0644 |
| R8 raw response store | `/private/var/db/edp-lab-r8-pr66-20261024` | root:wheel 0700; responses 0600 |

The exact [Watchdog plist](org.edp-lab.r4-watchdog-fixture.plist) has label
`org.edp-lab.r4-watchdog-fixture`, `StartInterval=30`, `RunAtLoad=false`,
and no `KeepAlive`. The exact [worker plist](org.edp-lab.r4-worker-fixture.plist)
uses only the no-write fixture worker in `unexpected` mode, with
`KeepAlive.SuccessfulExit=false` and `ThrottleInterval=30` for a bounded
restart/backoff observation. A nontransient blocked case is run manually,
outside the restart plist. Both plists use only the isolated fixture paths.
Neither references `org.edp-lab.day5-supervisor` or its Queue/state.

## Reviewed artifact pins (SHA-256)

| Artifact | SHA-256 |
| --- | --- |
| `/private/var/db/edp-lab/python/bin/python3.12` | `3274dde21f9767655564d093e63c9a5faacefbf1d41bc1e6bf8b6f6e5a441903` |
| `/opt/homebrew/bin/databricks` v1.21.0 | `00b2b4513660ea587ee5350b5030d6351d17cc326ca69fce4c60fdf9e538f303` |
| `src/edp_lab/__init__.py` | `661d3983f0e94938ba80e54d67479313ad2d1cdc8c706deba996baed824ec917` |
| `src/edp_lab/operating/__init__.py` | `96e2e1bdb7fc0de7574c6674f4a0c24715c1989043e089a0c057064658b3183b` |
| `src/edp_lab/operating/authority.py` | `3cad519172cc2ed3e1b5d8cff0d6632f22433667068b8eed5dd04d534a2876b3` |
| `src/edp_lab/operating/supervisor_health.py` | `ff8cc7a6c130229b485fc6be370710f751234e5f1cb4355e91f6edcf589c4ab6` |
| `src/edp_lab/operating/watchdog_delivery_r4.py` | `a0729374421a242473c4ad83bcbc22627378b15f50f9c6a2a50078648b2c7e83` |
| `src/edp_lab/operating/cli_preflight_r8.py` | `2c9c268b111705236845be930587f8d2dde5882e08239fc2e8b3e85407f777e3` |
| `scripts/r4_disposable_worker.py` | `fbf68bb887d3de11d137be0fcb1774bd03afbeccf37967a36e8ba8807468e1ce` |
| `scripts/owner_preflight_cli_r8.py` | `02f0c09d0c2ffa9aeb0aa69b78e6af381ef39fdc7b1597e3c56c3578aa4eff39` |
| [no-write Queue](no_write_queue.json) | `4ccaaa79246058ed2890687448f4ec04094f3075f3770392a40942718092a8e4` |
| [empty fixture ledger](operations.json) | `52717451535071393f53cfa2141e385baa2b890ddff67bac6584fe61af3e65ec` |
| [Watchdog config](watchdog.json) | `67d9252eeb83edd9c788c9ba8036d9e8bd36440bf9cc41890e6bdd714ed958d1` |
| [Watchdog plist](org.edp-lab.r4-watchdog-fixture.plist) | `cb7f446ff9c08543e0bf034aee78eefe78349b880a50caade512de637196d0f7` |
| [worker plist](org.edp-lab.r4-worker-fixture.plist) | `c6987fa8f96a239e47951aa41656a6a44ba316983bd4ff6962a15f7cf6023cc3` |
| `/usr/bin/mail` proposed notifier | `f45c1c18110703f1cd5ae80654f5d1763de84cb3e35c852e6a6da0950b7c47a0` |

The Owner must verify the remote PR HEAD and every copied hash against this
table before bootstrap or R8. A changed artifact invalidates this packet.

## Proposed notification route — separate final approval required

The exact [private config](watchdog.json) proposes
`alert_argv=["/usr/bin/mail", "-s", "EDP R4 fixture alert", "chengzhu13@gmail.com"]`
and `operator_id="Owner"`. The address is the authenticated `edp-lab`
principal observed in the local read-only smoke; it is **not yet an approved
notification destination**. No mail has been sent. The Owner must approve the
executable, argv and destination together. The acceptance run must retain a
delivery receipt and independent Owner acknowledgement. A successful mail
process exit alone is insufficient evidence of actual delivery.

## Exact privileged staging and activation commands — DO NOT RUN YET

Run from `/Users/lightnino/Projects/edp-lab-day5-e2e` only after final
approval and a clean, hash-verified PR #66 checkout. No command refers to
the historical Day 5 service.

```sh
sudo /bin/test ! -e /private/var/db/edp-lab-r4-fixture-20261024
sudo /bin/test ! -e /private/var/db/edp-lab-r8-pr66-20261024
sudo /bin/test ! -e /Library/LaunchDaemons/org.edp-lab.r4-watchdog-fixture.plist
sudo /bin/test ! -e /Library/LaunchDaemons/org.edp-lab.r4-worker-fixture.plist
sudo /usr/bin/install -d -m 0700 -o root -g wheel /private/var/db/edp-lab-r4-fixture-20261024
sudo /usr/bin/install -d -m 0700 -o root -g wheel /private/var/db/edp-lab-r4-fixture-20261024/queue /private/var/db/edp-lab-r4-fixture-20261024/ledger /private/var/db/edp-lab-r4-fixture-20261024/state /private/var/db/edp-lab-r4-fixture-20261024/config /private/var/db/edp-lab-r4-fixture-20261024/logs
sudo /usr/bin/install -d -m 0755 -o root -g wheel /private/var/db/edp-lab-r4-fixture-20261024/runtime /private/var/db/edp-lab-r4-fixture-20261024/runtime/src /private/var/db/edp-lab-r4-fixture-20261024/runtime/src/edp_lab /private/var/db/edp-lab-r4-fixture-20261024/runtime/src/edp_lab/operating /private/var/db/edp-lab-r4-fixture-20261024/runtime/scripts
sudo /usr/bin/install -d -m 0700 -o root -g wheel /private/var/db/edp-lab-r8-pr66-20261024
sudo /usr/bin/install -m 0600 -o root -g wheel docs/operating/r4_fixture_review/no_write_queue.json /private/var/db/edp-lab-r4-fixture-20261024/queue/no_write_queue.json
sudo /usr/bin/install -m 0600 -o root -g wheel docs/operating/r4_fixture_review/operations.json /private/var/db/edp-lab-r4-fixture-20261024/ledger/operations.json
sudo /usr/bin/install -m 0644 -o root -g wheel src/edp_lab/__init__.py /private/var/db/edp-lab-r4-fixture-20261024/runtime/src/edp_lab/__init__.py
sudo /usr/bin/install -m 0644 -o root -g wheel src/edp_lab/operating/__init__.py /private/var/db/edp-lab-r4-fixture-20261024/runtime/src/edp_lab/operating/__init__.py
sudo /usr/bin/install -m 0644 -o root -g wheel src/edp_lab/operating/authority.py /private/var/db/edp-lab-r4-fixture-20261024/runtime/src/edp_lab/operating/authority.py
sudo /usr/bin/install -m 0644 -o root -g wheel src/edp_lab/operating/supervisor_health.py /private/var/db/edp-lab-r4-fixture-20261024/runtime/src/edp_lab/operating/supervisor_health.py
sudo /usr/bin/install -m 0644 -o root -g wheel src/edp_lab/operating/watchdog_delivery_r4.py /private/var/db/edp-lab-r4-fixture-20261024/runtime/src/edp_lab/operating/watchdog_delivery_r4.py
sudo /usr/bin/install -m 0644 -o root -g wheel src/edp_lab/operating/cli_preflight_r8.py /private/var/db/edp-lab-r4-fixture-20261024/runtime/src/edp_lab/operating/cli_preflight_r8.py
sudo /usr/bin/install -m 0644 -o root -g wheel scripts/r4_disposable_worker.py /private/var/db/edp-lab-r4-fixture-20261024/runtime/scripts/r4_disposable_worker.py
sudo /usr/bin/install -m 0644 -o root -g wheel scripts/owner_preflight_cli_r8.py /private/var/db/edp-lab-r4-fixture-20261024/runtime/scripts/owner_preflight_cli_r8.py
```

The following installs the **proposed notifier configuration and launchd
services**; these three commands require the separate final Owner approval of
the mail route and exact plists, even after the root-owned directories exist:

```sh
sudo /usr/bin/install -m 0600 -o root -g wheel docs/operating/r4_fixture_review/watchdog.json /private/var/db/edp-lab-r4-fixture-20261024/config/watchdog.json
sudo /usr/bin/install -m 0644 -o root -g wheel docs/operating/r4_fixture_review/org.edp-lab.r4-watchdog-fixture.plist /Library/LaunchDaemons/org.edp-lab.r4-watchdog-fixture.plist
sudo /usr/bin/install -m 0644 -o root -g wheel docs/operating/r4_fixture_review/org.edp-lab.r4-worker-fixture.plist /Library/LaunchDaemons/org.edp-lab.r4-worker-fixture.plist
sudo /bin/launchctl bootstrap system /Library/LaunchDaemons/org.edp-lab.r4-watchdog-fixture.plist
sudo /bin/launchctl bootstrap system /Library/LaunchDaemons/org.edp-lab.r4-worker-fixture.plist
```

The worker service starts only when the Owner uses `launchctl kickstart`
for `system/org.edp-lab.r4-worker-fixture`; its nonzero fixture exit exercises
the configured 30-second backoff. The Watchdog has an independent 30-second
schedule. Do not leave the restart fixture running after the bounded test.
The exact observation and shutdown commands are:

```sh
sudo /bin/launchctl kickstart -k system/org.edp-lab.r4-worker-fixture
sudo /bin/launchctl print system/org.edp-lab.r4-worker-fixture
sudo /bin/launchctl print system/org.edp-lab.r4-watchdog-fixture
sudo /bin/launchctl bootout system/org.edp-lab.r4-worker-fixture
sudo /bin/launchctl bootout system/org.edp-lab.r4-watchdog-fixture
```

## R8 protected read-only command — DO NOT RUN YET

The 2026-10-23 **21:30–22:00 UTC** Query History window brackets the
original P11 investigation window and is bounded to 30 minutes. The exact
target is the already existing Day 5 roster table. The command performs
`current-user me`, paginated Query History GETs and one exact UC table GET.
It has no SQL submission, grant, installer or credential-write step.

```sh
sudo /usr/bin/env -i PATH=/opt/homebrew/bin:/usr/bin:/bin HOME=/private/var/db/edp-lab/private/home DATABRICKS_CONFIG_FILE=/private/var/db/edp-lab/private/databrickscfg DATABRICKS_AUTH_STORAGE=plaintext PYTHONPATH=/private/var/db/edp-lab-r4-fixture-20261024/runtime/src /private/var/db/edp-lab/python/bin/python3.12 /private/var/db/edp-lab-r4-fixture-20261024/runtime/scripts/owner_preflight_cli_r8.py --cli /opt/homebrew/bin/databricks --profile edp-lab --expected-user chengzhu13@gmail.com --table workspace.edp_lab.n500_input_roster_day5_v1 --expected-uc-state PRESENT --start-ms 1792791000000 --end-ms 1792792800000 --protected-evidence-dir /private/var/db/edp-lab-r8-pr66-20261024
```

The root-owned response sink creates `identity.stdout.bin`,
`identity.stderr.bin`, `history-000.stdout.bin`, `history-000.stderr.bin`,
and `uc-target.stdout.bin`/`uc-target.stderr.bin`, all 0600. If History
paginates, each further page is stored with an incrementing name. Its
sanitized summary binds SHA-256 hashes of every response. The Owner must
independently hash the saved files and compare the output, inspect effective
profile/identity and pre/post protected credential-file hashes, and stop if
the CLI requires auth login. **A profile that refreshes/writes its auth cache
would violate the no-credential-modification boundary; confirm the protected
profile's non-writing behavior before this command, not only afterward.** If
an unexpected credential change occurs, record it as a failed acceptance and
stop. Reuse of this
evidence directory fails closed because files are created exclusively.

## Protected acceptance evidence to capture after approval

Capture independently, under root-owned evidence storage: copied artifact
hashes and permissions; launchd `print` output for both fixture labels;
normal, blocked `SQL_STATEMENT_ID_MISSING`, unexpected, SIGKILL, hung-heartbeat
and live-process no-progress statuses; restart timestamps showing backoff;
Watchdog failure and notifier failure; exact email delivery and Owner
acknowledgement; sanitized status projection; and fixture Queue/ledger hashes
before and after. The fixture ledger must remain empty. The fixture worker
receives no Databricks credential variables or config path, imports no
Databricks adapter, and must have zero SQL submissions and external effects.
Because the fixture process runs as root on the existing host, the Owner must
inspect the actual service environment and host access boundary before
accepting credential isolation. The historical Day 5
Supervisor must remain stopped and its protected checkpoint/ledger unchanged.

**Current gate:** R4 protected-live BLOCKED; R8 protected Owner-terminal
BLOCKED. Passing this fixture is evidence for these reviewed components only,
not deployment of production monitoring for future workflows. PR #66 remains
unmerged pending separate Owner approval.
