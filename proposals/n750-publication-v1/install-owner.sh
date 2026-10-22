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
assert sha(proposal) == 'aabdf5968e46daf7d27b4faac32d76fd0872fd48d6e74a3bbf9465e53401cd20', 'Owner-reviewed proposal changed'
grant = json.loads(proposal)
assert grant['status'] == 'PENDING_OWNER_REVIEW'
for relative, digest in grant['execution_files_sha256'].items():
    assert sha(Path(relative).read_bytes()) == digest, relative
grant['status'] = 'OWNER_APPROVED'
approved = encoded(grant)
assert sha(approved) == '17149640035bc436f83ef3a0c2c66f766005d7e902bb8e2b30042b91b8b8771f'
host = Path('src/edp_lab/ingestion/n450_authorization.py')
source = host.read_bytes()
assert sha(source) in ('79b5620d2f9bf7acd3d537f7ee0188ced447eb2da2c6e373032cda0025f772c8', 'acb8b8bc262ef9b07221ce6616e303c65f988e1fd31b7c21a43753d6052c91c4'), 'Trusted host changed'
original = Path('metadata/authorizations/n450_processing_v6.json')
assert sha(original.read_bytes()) == 'de242d3754688288cb174fbfde2f8cbc6594fc80b36a8d6281726ca9479322e7'
updated, count = re.subn(r'^OWNER_GRANT_SHA256 = .*$', 'OWNER_GRANT_SHA256 = "17149640035bc436f83ef3a0c2c66f766005d7e902bb8e2b30042b91b8b8771f"', source.decode(), flags=re.M)
assert count == 1
updated, count = re.subn(r'^OWNER_GRANT_PATH = .*$', 'OWNER_GRANT_PATH = Path("metadata/authorizations/n750_admission_v1.json")', updated, flags=re.M)
assert count == 1
updated = updated.encode()
assert sha(updated) == 'acb8b8bc262ef9b07221ce6616e303c65f988e1fd31b7c21a43753d6052c91c4'
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
assert sha(host.read_bytes()) == 'acb8b8bc262ef9b07221ce6616e303c65f988e1fd31b7c21a43753d6052c91c4'
assert sha(target.read_bytes()) == '17149640035bc436f83ef3a0c2c66f766005d7e902bb8e2b30042b91b8b8771f'
assert sha(original.read_bytes()) == 'de242d3754688288cb174fbfde2f8cbc6594fc80b36a8d6281726ca9479322e7'
print('Existing owner pin installed. No admission, freeze, upload or processing executed.')
OWNER_PY
