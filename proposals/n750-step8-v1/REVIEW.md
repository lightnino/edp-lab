# N750 Step 8 owner checkpoint

**Decision requested:** approve the exact pending [owner record](owner-record.proposed.json) for Step 8 remote RAW resolution and processing. Its SHA-256 is `0c0571e45de48ea96ebac0c6d6a28a2cf6c6ee5086558da23087014d07f05b36`. The canonical `OWNER_APPROVED` record, obtained by changing only `status`, must hash to `5ae18d7d2ee770cbefb3f6ad0a6b05eac87282d8e88b2c9f6422dff7c9b7b120`.

The grant covers exactly frozen N750: 750 bindings, SRC010451–SRC011200, with 745 SEC Daily Master and five Treasury XML sources. Ten pinned files bind its roster, hashes, C1500 freeze, prior admission approval, remote evidence, approved M2 contract and converter. Existing remote evidence is 450 previously verified and 300 unverified. It does not establish that the 300 are absent or corrupt. The owner would authorize searching for exact objects first, conditional upload of matching original bytes for the 300 if needed, and independent SHA readback before processing each source. Processing covers M1 lexical output for SEC and only the contract's Treasury property allowlist for M2, followed by versioned CLEAN/QUERYABLE publication and independent validation. Historical C750 outputs, RAW, admission membership, semantic mappings and Step 9 remain outside scope.

The existing trusted owner pattern is [Step 1's installation procedure](../n750-publication-v1/install-owner.sh): verify the reviewed proposal and every pinned file; change only `status` in canonical JSON; verify the expected approved hash; exclusively create the approved record; install a trusted host pin; verify final hashes. Step 1's installer targets the integration worktree and admission grant and must **not** be rerun for Step 8. The current admission pin in `n450_authorization.py` stays untouched. The separate, fail-closed [Step 8 pin check](../../src/edp_lab/ingestion/n750_step8_authorization.py) starts with `N750_OWNER_GRANT_SHA256 = None`, so this proposal cannot authorize itself.

After explicit owner approval, the owner should run the following from a trusted terminal. This is the same installation method used for Step 1, scoped to the Step 8 record and pin. It writes only `metadata/authorizations/n750_processing_v1.json` and the one Step 8 pin line; it performs no RAW transfer or processing.

```sh
cd /Users/lightnino/Projects/edp-lab-day3-authorized/runs/day4/n750-step8-worktree
PYTHONPATH=src /Users/lightnino/Projects/edp-lab/.venv/bin/python - <<'OWNER_PY'
import hashlib, json, os
from pathlib import Path

sha = lambda data: hashlib.sha256(data).hexdigest()
encoded = lambda value: (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
proposal_path = Path('proposals/n750-step8-v1/owner-record.proposed.json')
proposal = proposal_path.read_bytes()
assert sha(proposal) == '0c0571e45de48ea96ebac0c6d6a28a2cf6c6ee5086558da23087014d07f05b36'
grant = json.loads(proposal)
assert grant['status'] == 'PENDING_OWNER_REVIEW' and encoded(grant) == proposal
for relative, digest in grant['input_files_sha256'].items():
    assert sha(Path(relative).read_bytes()) == digest, relative
grant['status'] = 'OWNER_APPROVED'
approved = encoded(grant)
assert sha(approved) == '5ae18d7d2ee770cbefb3f6ad0a6b05eac87282d8e88b2c9f6422dff7c9b7b120'

host = Path('src/edp_lab/ingestion/n750_step8_authorization.py')
before = host.read_bytes()
assert sha(before) == 'bc449f0b1fb481eedfad76de138155944c435bf12b1e5cc39cdaf72bc48d9d8c'
old = b'N750_OWNER_GRANT_SHA256 = None'
new = b'N750_OWNER_GRANT_SHA256 = "5ae18d7d2ee770cbefb3f6ad0a6b05eac87282d8e88b2c9f6422dff7c9b7b120"'
assert before.count(old) == 1
after = before.replace(old, new)
assert sha(after) == '82c78933b4ace7a0b2b8e9009e3c9ee3f6395c92cb05e3cffa2d33c60d633bad'

target = Path('metadata/authorizations/n750_processing_v1.json')
with target.open('xb') as stream:
    stream.write(approved)
temporary = host.with_name(host.name + '.owner-install.tmp')
with temporary.open('xb') as stream:
    stream.write(after)
os.chmod(temporary, host.stat().st_mode)
os.replace(temporary, host)
assert sha(target.read_bytes()) == '5ae18d7d2ee770cbefb3f6ad0a6b05eac87282d8e88b2c9f6422dff7c9b7b120'
assert sha(host.read_bytes()) == '82c78933b4ace7a0b2b8e9009e3c9ee3f6395c92cb05e3cffa2d33c60d633bad'
print('N750 Step 8 owner grant installed; no RAW transfer or processing run')
OWNER_PY
```

If any assertion fails, stop; do not substitute files or change a digest. Once approval and this trusted installation are confirmed, Step 8 resumes from this checkpoint. The runtime still must verify each remote object's exact frozen SHA before processing and produce independent persisted-output evidence before claiming completion.
