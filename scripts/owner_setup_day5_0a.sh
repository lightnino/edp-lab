#!/bin/zsh
# Run only in the owner's Terminal, never through Codex. No private key is printed.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd -P)"
base="/private/var/db/edp-lab"
trust="$base/trust"
private="$base/private"
runtime="$base/runtime"

if [[ "$(id -u)" != 0 ]]; then
  print -u2 "Run with sudo in the owner's Terminal."
  exit 1
fi
if [[ -e "$base" ]]; then
  print -u2 "Protected 0A directory already exists; refusing to overwrite it."
  exit 1
fi

install -d -m 755 -o root -g wheel "$base" "$trust" "$base/grants" "$runtime"
install -d -m 700 -o root -g wheel "$private" "$base/ledger"
/usr/bin/ditto "$root/src/edp_lab" "$runtime/edp_lab"
chown -R root:wheel "$runtime"
chmod -R go-w "$runtime"
for role in owner broker verifier; do
  /opt/homebrew/bin/openssl genpkey -algorithm Ed25519 -out "$private/${role}.pem"
  chmod 600 "$private/${role}.pem"
  /opt/homebrew/bin/openssl pkey -in "$private/${role}.pem" -pubout \
    -out "$trust/${role}_ed25519_public.pem"
  chmod 644 "$trust/${role}_ed25519_public.pem"
done
print '[]' > "$trust/revoked_grants.json"
chmod 644 "$trust/revoked_grants.json"
print "0A key and runtime installation complete at $base"
print "Private keys are root-only; no policy, prior receipt or broker service is active yet."
