"""Read-only remote byte verification of explicit proposal objects; no upload/jobs."""
import hashlib
import json
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'proposals/n450-v1'


def main():
    if not __debug__:
        raise RuntimeError("Optimized execution is forbidden for proposal verification")
    roster = json.loads((OUT / 'roster.json').read_text())
    receipts = {}
    evidence = {}
    for day in [3, 4, 5]:
        base = Path(f'/Users/lightnino/Projects/edp-lab-day{day}')
        for path in base.glob('runs/*/upload-v*/completion.json'):
            raw = path.read_bytes()
            evidence[str(path)] = hashlib.sha256(raw).hexdigest()
            for receipt in json.loads(raw)['receipts']:
                receipts[receipt['sha256']] = receipt

    def verify(member):
        prior = receipts.get(member['raw_sha256'])
        result = {'source_identity': member['source_identity'], 'expected_sha256': member['raw_sha256'],
                      'processing_authorization': 'NOT_AUTHORIZED', 'local_original': 'EXACT_HASH_PASS'}
        if prior is None:
            return dict(result, remote_status='NO_KNOWN_LOCATION', upload='OWNER_AUTHORIZATION_REQUIRED_IF_NO_REUSE_LOCATION')
        remote = prior['remote']
        assert remote.startswith('dbfs:/Volumes/workspace/edp_lab/raw/')
        with tempfile.TemporaryDirectory(prefix='n450-verify-') as tmp:
            target = Path(tmp) / 'object'
            proc = subprocess.run(['databricks', 'fs', 'cp', remote, str(target), '-p', 'edp-lab'],
                                  check=False, capture_output=True, text=True, timeout=180)
            if proc.returncode:
                return dict(result, remote=remote, remote_status='READ_FAILED', error=proc.stderr)
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            return dict(result, remote=remote, actual_sha256=actual, bytes=target.stat().st_size,
                        remote_status='EXACT_REMOTE_BYTES_PASS' if actual == member['raw_sha256'] and target.stat().st_size == member['bytes'] else 'INTEGRITY_FAILED',
                        historical_registered_alias=prior['source_instance_id'],
                        upload='NOT_NEEDED_IF_OWNER_APPROVES_EXACT_OBJECT_REUSE',
                        verified_at_utc=datetime.now(UTC).isoformat())

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = []
        for result in pool.map(verify, roster):
            results.append(result)
            if len(results) % 50 == 0:
                print(f'verified {len(results)}/450', flush=True)
    report = {'checked_at_utc': datetime.now(UTC).isoformat(), 'objects': results,
                  'evidence_sha256': evidence, 'method': '450 explicit remote objects downloaded to temporary verification files, SHA-256 and size compared, no upload or compute',
                  'immutable_location': 'UNVERIFIED: UC volume permits writes; owner must approve exact object reuse and require pre-read hashes/version protection',
                  'proposal_roster_sha256': hashlib.sha256((OUT / 'roster.json').read_bytes()).hexdigest()}
    with (OUT / 'remote-live.json').open('x') as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write('\n')
    from collections import Counter
    print(dict(Counter(r['remote_status'] for r in results)), flush=True)


if __name__ == '__main__':
    main()
