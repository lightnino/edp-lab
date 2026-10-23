#!/bin/zsh
# Targeted protected credential repair. Never prints a token or private key.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd -P)"
base="/private/var/db/edp-lab"
private="$base/private"
runtime="$base/runtime"
config="$private/databrickscfg"
auth_home="$private/home"
profile="edp-lab"
host="https://dbc-23e7784b-bb6e.cloud.databricks.com"
remote="dbfs:/Volumes/workspace/edp_lab/raw"

if [[ "$(id -u)" != 0 || ! -f "$private/owner.pem" ||
      ! -f "$base/receipts/c1500-prior.json" ]]; then
  print -u2 "Existing protected 0A deployment and root identity required."
  exit 1
fi
if [[ -n "$(/usr/bin/git -c safe.directory="$root" -C "$root" status --porcelain --untracked-files=no)" ]]; then
  print -u2 "Tracked checkout is modified; use the pinned clean commit."
  exit 1
fi
if /bin/launchctl print system/org.edp-lab.day5-supervisor | /usr/bin/grep -q 'state = running'; then
  print -u2 "Day 5 supervisor is running; refusing code replacement."
  exit 1
fi

install -d -m 700 -o root -g wheel "$auth_home"
if [[ ! -e "$config" ]]; then
  /bin/cat > "$config" <<EOF
[__settings__]
auth_storage = plaintext

[$profile]
host = $host
auth_type = databricks-cli
account_id = 088be824-cc54-47cf-bcde-d5de77bbe82d
workspace_id = 7474654544694838
EOF
  chown root:wheel "$config"
  chmod 600 "$config"
fi
if [[ "$(stat -f '%Su:%Lp' "$config")" != "root:600" ]]; then
  print -u2 "Protected Databricks configuration permissions are invalid."
  exit 1
fi
export HOME="$auth_home"
export DATABRICKS_CONFIG_FILE="$config"
export DATABRICKS_AUTH_STORAGE="plaintext"
if ! /opt/homebrew/bin/databricks fs ls "$remote" -p "$profile" -o json >/dev/null 2>&1; then
  print "One-time protected Databricks OAuth login follows. Complete the browser challenge as the existing EDP Lab user."
  /opt/homebrew/bin/databricks auth login --host "$host" --profile "$profile" --timeout 20m
fi
/opt/homebrew/bin/databricks fs ls "$remote" -p "$profile" -o json >/dev/null
auth_description="$(/opt/homebrew/bin/databricks auth describe -p "$profile")"
if [[ "$auth_description" != *"User: chengzhu13@gmail.com"* ||
      "$auth_description" != *"Token storage: plaintext"* ]]; then
  print -u2 "Protected identity or token storage did not match the reviewed scope."
  exit 1
fi

if /bin/launchctl print system/org.edp-lab.policy-broker >/dev/null 2>&1; then
  /bin/launchctl bootout system/org.edp-lab.policy-broker
fi
/usr/bin/git -c safe.directory="$root" -C "$root" archive HEAD src/edp_lab | \
  /usr/bin/tar -x -C "$runtime"
chown -R root:wheel "$runtime"
chmod -R go-w "$runtime"
broker_plist="/Library/LaunchDaemons/org.edp-lab.policy-broker.plist"
/bin/cat > "$broker_plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>org.edp-lab.policy-broker</string>
<key>ProgramArguments</key><array>
<string>$base/python/bin/python3.12</string><string>-m</string>
<string>edp_lab.operating.policy_broker</string>
<string>$base/broker.sock</string><string>$root</string>
<string>$base/trust/standing_policy_v1.json</string><string>$base/trust</string>
<string>$private/broker.pem</string><string>$base/grants</string>
<string>--git-user</string><string>lightnino</string>
</array>
<key>EnvironmentVariables</key><dict>
<key>PYTHONPATH</key><string>$runtime/src</string>
<key>PATH</key><string>/opt/homebrew/bin:/usr/bin:/bin</string>
<key>HOME</key><string>$auth_home</string>
<key>DATABRICKS_CONFIG_FILE</key><string>$config</string>
<key>DATABRICKS_AUTH_STORAGE</key><string>plaintext</string>
</dict>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
<key>StandardOutPath</key><string>$base/broker.stdout.log</string>
<key>StandardErrorPath</key><string>$base/broker.stderr.log</string>
</dict></plist>
EOF
chown root:wheel "$broker_plist"
chmod 644 "$broker_plist"
/bin/launchctl bootstrap system "$broker_plist"

supervisor_plist="/Library/LaunchDaemons/org.edp-lab.day5-supervisor.plist"
if /bin/launchctl print system/org.edp-lab.day5-supervisor >/dev/null 2>&1; then
  /bin/launchctl bootout system/org.edp-lab.day5-supervisor
fi
/bin/cat > "$supervisor_plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>org.edp-lab.day5-supervisor</string>
<key>ProgramArguments</key><array>
<string>$base/python/bin/python3.12</string><string>-m</string>
<string>edp_lab.operating.checkpoint_supervisor</string>
<string>$root</string><string>$root/runs/day5/c2000_live_queue_v1.json</string>
<string>$base/state/day5</string><string>$base/trust</string>
<string>$base/broker.sock</string><string>$private/verifier.pem</string>
</array>
<key>EnvironmentVariables</key><dict>
<key>PYTHONPATH</key><string>$runtime/src</string>
<key>PATH</key><string>/opt/homebrew/bin:/usr/bin:/bin</string>
<key>HOME</key><string>$auth_home</string>
<key>DATABRICKS_CONFIG_FILE</key><string>$config</string>
<key>DATABRICKS_AUTH_STORAGE</key><string>plaintext</string>
</dict>
<key>RunAtLoad</key><true/><key>KeepAlive</key><false/>
<key>StandardOutPath</key><string>$base/supervisor.stdout.log</string>
<key>StandardErrorPath</key><string>$base/supervisor.stderr.log</string>
</dict></plist>
EOF
chown root:wheel "$supervisor_plist"
chmod 644 "$supervisor_plist"
/bin/launchctl bootstrap system "$supervisor_plist"
print "Protected credential repair deployed. Existing keys, policy, prior receipt, grant, and ledger were retained."
print "The supervisor will verify no ledger reservation and no remote object before resetting raw-001."
