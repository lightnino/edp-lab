#!/bin/zsh
# Run only in the owner's Terminal, never through Codex. No private key is printed.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd -P)"
base="/private/var/db/edp-lab"
trust="$base/trust"
private="$base/private"
runtime="$base/runtime"
python_source="/Users/lightnino/.local/share/uv/python/cpython-3.12-macos-aarch64-none"
policy_source="$root/runs/day5/standing_policy_unsigned_v1.json"
queue_source="$root/runs/day5/c2000_live_queue_v1.json"
policy_sha="7940e558b270418177b54eae40673064af71a2b60ac05c562d7e31b30d8f69b2"
queue_sha="e43cf9984e1c54b17cbdc44917954bf802acba3241168ea353b302ec41076e34"

if [[ "$(id -u)" != 0 ]]; then
  print -u2 "Run with sudo in the owner's Terminal."
  exit 1
fi
if [[ -e "$base" ]]; then
  print -u2 "Protected 0A directory already exists; refusing to overwrite it."
  exit 1
fi
if [[ "$(/usr/bin/shasum -a 256 "$policy_source" | /usr/bin/awk '{print $1}')" != "$policy_sha" ||
      "$(/usr/bin/shasum -a 256 "$queue_source" | /usr/bin/awk '{print $1}')" != "$queue_sha" ]]; then
  print -u2 "Reviewed standing policy or Day 5 queue hash changed."
  exit 1
fi

install -d -m 755 -o root -g wheel "$base" "$trust" "$base/grants" \
  "$base/receipts" "$runtime"
install -d -m 700 -o root -g wheel "$private" "$base/ledger"
/usr/bin/ditto "$root/src/edp_lab" "$runtime/edp_lab"
/usr/bin/ditto "$python_source" "$base/python"
chown -R root:wheel "$runtime"
chmod -R go-w "$runtime"
chown -R root:wheel "$base/python"
chmod -R go-w "$base/python"
for role in owner broker verifier; do
  /opt/homebrew/bin/openssl genpkey -algorithm Ed25519 -out "$private/${role}.pem"
  chmod 600 "$private/${role}.pem"
  /opt/homebrew/bin/openssl pkey -in "$private/${role}.pem" -pubout \
    -out "$trust/${role}_ed25519_public.pem"
  chmod 644 "$trust/${role}_ed25519_public.pem"
done
print '[]' > "$trust/revoked_grants.json"
chmod 644 "$trust/revoked_grants.json"
/usr/bin/install -m 644 -o root -g wheel "$policy_source" "$base/standing_policy_unsigned_v1.json"
/opt/homebrew/bin/openssl pkeyutl -sign -inkey "$private/owner.pem" -rawin \
  -in "$base/standing_policy_unsigned_v1.json" -out "$private/policy.sig"
POLICY_BASE="$base" "$base/python/bin/python3.12" - <<'PY'
import base64
import json
import os
from pathlib import Path

base = Path(os.environ["POLICY_BASE"])
document = json.loads((base / "standing_policy_unsigned_v1.json").read_bytes())
signature = (base / "private/policy.sig").read_bytes()
envelope = {"document": document, "signature_base64": base64.b64encode(signature).decode()}
(base / "trust/standing_policy_v1.json").write_text(
    json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
PY
chmod 644 "$trust/standing_policy_v1.json"
PYTHONPATH="$runtime" "$base/python/bin/python3.12" -m edp_lab.operating.prior_verifier \
  "$root" "$trust" "$private/verifier.pem" "$base/receipts/c1500-prior.json" \
  --databricks-user lightnino
plist="/Library/LaunchDaemons/org.edp-lab.policy-broker.plist"
if [[ -e "$plist" ]]; then
  print -u2 "Broker launch definition already exists; refusing to replace it."
  exit 1
fi
/bin/cat > "$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>org.edp-lab.policy-broker</string>
<key>ProgramArguments</key><array>
<string>$base/python/bin/python3.12</string>
<string>-m</string><string>edp_lab.operating.policy_broker</string>
<string>$base/broker.sock</string><string>$root</string>
<string>$trust/standing_policy_v1.json</string><string>$trust</string>
<string>$private/broker.pem</string><string>$base/grants</string>
<string>--databricks-user</string><string>lightnino</string>
<string>--git-user</string><string>lightnino</string>
</array>
<key>EnvironmentVariables</key><dict>
<key>PYTHONPATH</key><string>$runtime</string>
</dict>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
<key>StandardOutPath</key><string>$base/broker.stdout.log</string>
<key>StandardErrorPath</key><string>$base/broker.stderr.log</string>
</dict></plist>
EOF
chown root:wheel "$plist"
chmod 644 "$plist"
/bin/launchctl bootstrap system "$plist"
print "Protected 0A keys, standing policy, independently signed C1500 receipt and broker installed."
print "Private keys remain root-only. The Day 5 queue is pinned at SHA-256 $queue_sha."
