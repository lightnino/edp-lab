"""Read-only original-evidence qualification; writes proposals only, grants no authority."""
import csv
import hashlib
import io
import json
import re
from collections import Counter
from pathlib import Path

from edp_lab.ingestion.universe import ScopeDenied, UniverseGate, processing

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'proposals/n450-v1'
LAB = Path('/Users/lightnino/Projects/edp-lab')


def digest(path):
    return hashlib.file_digest(Path(path).open('rb'), 'sha256').hexdigest()


def main():
    if not __debug__:
        raise RuntimeError("Optimized execution is forbidden for proposal verification")
    evidence = {}

    def read(path, expected=None):
        path = Path(path)
        raw = path.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if expected is not None and actual != expected:
            raise ValueError(f'Changed evidence: {path}')
        evidence[str(path)] = actual
        return raw

    gate = UniverseGate.load(ROOT)
    gate.verify_inventory(ROOT)
    doc = gate.document()
    assert doc['member_count'] == 3021
    members = {m['identity']: m for m in doc['members']}
    held = {i for i, m in members.items() if m['holdout']}
    assert len(held) == 41
    side = json.loads(read(ROOT / 'metadata/source_universes/historical_cohort_bindings_v1.json'))
    c300 = {b['delivery_identity'] for b in side['bindings']
            if b['identity'] in side['cohorts']['C300']['identities']}
    assert len(c300) == 300
    for rel in ['metadata/source_universes/approved_v1/manifest.json',
                'metadata/source_universes/approved_v1/owner_authorization.json']:
        read(ROOT / rel)
    inventory = list(csv.DictReader(io.StringIO(read(doc['inventory_reference'], doc['inventory_sha256']).decode())))
    indexed = {r['inventory_id']: r for r in inventory}
    hashes = Counter(r['sha256'] for r in inventory)
    admitted = list(csv.DictReader((ROOT / 'metadata/corpus_manifest_v3.csv').open()))
    old_hashes = {r['raw_sha256'] for r in admitted}
    active = json.loads(read(LAB / 'runs/whole_lab/active-inventory.json'))
    review_path = Path(active['review_inventory'])
    review = json.loads(read(review_path, active['review_inventory_sha256']))
    plan = json.loads(read(review_path.parent / 'candidates.json'))
    planned = {c['candidate_id']: c for c in plan['candidates']}
    assert review['plan_sha256'] == plan['plan_sha256']
    selected = []
    # Stable original review order; one family avoids unnecessary new format scope.
    for entry in review['entries']:
        if entry['origin'] != 'ACQUIRED':
            continue
        record = entry['record']
        candidate = record['candidate']
        identity = entry['delivery_candidate_id']
        if candidate['family'] != 'SEC_EDGAR_DAILY_MASTER' or identity in c300 or identity in held:
            continue
        r = indexed[identity]
        if hashes[r['sha256']] != 1 or r['sha256'] in old_hashes:
            continue
        assert candidate == planned[candidate['candidate_id']]
        assert record['plan_sha256'] == plan['plan_sha256']
        assert record['status'] == 'MECHANICALLY_VERIFIED_CANDIDATE'
        assert record['inspection']['physical_format_check'] == 'PASS'
        assert r['status'] == 'VERIFIED_CANDIDATE_FOR_ADMISSION_REVIEW'
        assert (r['publisher'], r['family'], r['publisher_url']) == (candidate['publisher'], candidate['family'], candidate['url'])
        assert record == json.loads(read(review_path.parent / f"delivery-{candidate['candidate_id']}.json"))
        cap = record['capture']
        receipt_path = review_path.parent / cap['receipt']
        receipt = json.loads(read(receipt_path, cap['receipt_sha256']))
        assert receipt['status'] == 'COMPLETE' and receipt['curl_exit_code'] == 0
        assert receipt['requested_url'] == candidate['url']
        assert receipt['started_at_utc'] and receipt['finished_at_utc']
        assert receipt['sha256'] == cap['sha256'] == r['sha256']
        assert receipt['bytes'] == int(r['bytes']) == Path(r['final_path']).stat().st_size
        assert digest(r['final_path']) == r['sha256']
        gate.check(identity, r['sha256'], r['final_path'])  # Eligibility only.
        selected.append({'proposal_position': len(selected)+1, 'source_identity': identity,
                             'candidate_id': candidate['candidate_id'], 'family': r['family'], 'edition': candidate['edition'],
                             'raw_path': r['final_path'], 'raw_sha256': r['sha256'], 'bytes': int(r['bytes']),
                             'publisher_url': candidate['url'], 'receipt_path': str(receipt_path),
                             'receipt_sha256': cap['receipt_sha256'], 'qualification': 'PASS_MECHANICAL_ONLY',
                             'processing_authorization': 'NOT_AUTHORIZED'})
        if len(selected) == 450:
            break
    assert len(selected) == len({m['source_identity'] for m in selected}) == 450
    assert len({m['raw_sha256'] for m in selected}) == 450
    assert len({m['raw_path'] for m in selected}) == 450
    outside_text = read(doc['outside_universe_policy']['reference'], doc['outside_universe_policy']['sha256']).decode()
    blocks = re.findall(r'^## (SRC\d+)\n(.*?)(?=^## SRC|\Z)', outside_text, re.MULTILINE | re.DOTALL)
    assert len(blocks) == 800
    outside_hashes = {re.search(r'RAW SHA-256: `([a-f0-9]+)`', b)[1] for _, b in blocks}
    assert not outside_hashes & {m['raw_sha256'] for m in doc['members']}
    sid, block = blocks[0]
    path = re.search(r'- Local: `([^`]+)`', block)[1]
    expected = re.search(r'RAW SHA-256: `([a-f0-9]+)`', block)[1]
    assert digest(path) == expected
    binding = {'source_instance_id': sid, 'raw_sha256': expected, 'raw_path': path}
    # Actual processing authorization entrypoint; no RAW consumer is invoked.
    try:
        processing(ROOT, binding, 'N450')
        raise AssertionError('Unauthorized entrypoint accepted source')
    except ScopeDenied as exc:
        assert exc.outcome['reason'] == 'NOT_IN_APPROVED_UNIVERSE'
        negative = {'valid_local_sha256': True, 'entrypoint': 'edp_lab.ingestion.universe.processing',
                        'outcome': exc.outcome, 'side_effects': 'NONE: entrypoint performs authority checks only'}
    first = selected[0]
    try:
        gate.check(first['source_identity'], first['raw_sha256'], first['raw_path'], cohort='N450')
        raise AssertionError('Proposal granted authority')
    except ScopeDenied as exc:
        assert exc.outcome['reason'] == 'NOT_IN_PINNED_COHORT'
    report = {'status': 'PROPOSAL_ONLY_OWNER_REVIEW_REQUIRED', 'universe': gate.scope_reference(),
                  'original_members': 3021, 'proposed': 450, 'family_counts': dict(Counter(m['family'] for m in selected)),
                  'excluded_c300': sorted(c300), 'excluded_holdouts': sorted(held), 'excluded_outside_ids': [i for i, _ in blocks],
                  'qualification': '450 exact local SHA-256, size, pinned inventory/review, plan/delivery, publisher receipts PASS; no parsing',
                  'local_bytes': sum(m['bytes'] for m in selected), 'negative_test': negative,
                  'evidence_sha256': evidence, 'selection': 'First 450 eligible SEC_EDGAR_DAILY_MASTER in pinned original review order; no acquisition',
                  'frozen_or_admitted': False, 'new_registered_ids_assigned': False}
    for path, expected_hash in evidence.items():
        assert digest(path) == expected_hash
    OUT.mkdir(parents=True, exist_ok=True)
    for name, obj in [('roster.json', selected), ('qualification.json', report)]:
        with (OUT / name).open('x') as f:
            json.dump(obj, f, indent=2, sort_keys=True)
            f.write('\n')
    print(json.dumps({k: report[k] for k in ['status', 'proposed', 'family_counts', 'local_bytes']}))


if __name__ == '__main__':
    main()
