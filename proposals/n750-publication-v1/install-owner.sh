#!/bin/sh
# OWNER/TRUSTED TERMINAL ONLY. Agent preparation is not approval.
set -eu
cd /Users/lightnino/Projects/edp-lab-day3-authorized/runs/day4/integration-worktree
PYTHONPATH=src /Users/lightnino/Projects/edp-lab/.venv/bin/python - <<'OWNER_PY'
import json, os, re
from pathlib import Path
from edp_lab.ingestion.c300_admission import encoded
from edp_lab.ingestion.universe import sha
proposal = Path('proposals/n750-publication-v1/owner-record.proposed.json').read_bytes()
assert sha(proposal) == 'dd3d5db867c3247c101271d6d6f389385e1add88dd1c42bf615e7e02b5951e15', 'Owner-reviewed proposal changed'
grant = json.loads(proposal)
assert grant['status'] == 'PENDING_OWNER_REVIEW'
for relative, digest in grant['execution_files_sha256'].items():
    assert sha(Path(relative).read_bytes()) == digest, relative
grant['status'] = 'OWNER_APPROVED'
approved = encoded(grant)
assert sha(approved) == '46488e49d34abd2160ad15089581c01c74325714e6d8cc57a27eb1d8e3bd5001'
host = Path('src/edp_lab/ingestion/n450_authorization.py')
source = host.read_bytes()
assert sha(source) in ('79b5620d2f9bf7acd3d537f7ee0188ced447eb2da2c6e373032cda0025f772c8', 'b81a4cb31a848e2e4aca620efa1bb15dcccb104d98c2d366f632d4a69fa3d0c5'), 'Trusted host changed'
original = Path('metadata/authorizations/n450_processing_v6.json')
assert sha(original.read_bytes()) == 'de242d3754688288cb174fbfde2f8cbc6594fc80b36a8d6281726ca9479322e7'
updated, count = re.subn(r'^OWNER_GRANT_SHA256 = .*$', 'OWNER_GRANT_SHA256 = "46488e49d34abd2160ad15089581c01c74325714e6d8cc57a27eb1d8e3bd5001"', source.decode(), flags=re.M)
assert count == 1
updated, count = re.subn(r'^OWNER_GRANT_PATH = .*$', 'OWNER_GRANT_PATH = Path("metadata/authorizations/n750_admission_v1.json")', updated, flags=re.M)
assert count == 1
updated = updated.encode()
assert sha(updated) == 'b81a4cb31a848e2e4aca620efa1bb15dcccb104d98c2d366f632d4a69fa3d0c5'
target = Path('metadata/authorizations/n750_admission_v1.json')
if target.exists():
    assert target.read_bytes() == approved
else:
    with target.open('xb') as stream:
        stream.write(approved)
if source != updated:
    temporary = host.with_name(host.name + '.owner-install.tmp')
    with temporary.open('xb') as stream:
        stream.write(updated)
    os.chmod(temporary, host.stat().st_mode)
    os.replace(temporary, host)
assert sha(host.read_bytes()) == 'b81a4cb31a848e2e4aca620efa1bb15dcccb104d98c2d366f632d4a69fa3d0c5'
assert sha(target.read_bytes()) == '46488e49d34abd2160ad15089581c01c74325714e6d8cc57a27eb1d8e3bd5001'
assert sha(original.read_bytes()) == 'de242d3754688288cb174fbfde2f8cbc6594fc80b36a8d6281726ca9479322e7'
print('Existing owner pin installed. No admission, freeze, upload or processing executed.')
OWNER_PY
