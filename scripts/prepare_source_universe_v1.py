"""Offline, exclusive-create pending universe proposal; never activates the host gate."""
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LAB = Path('/Users/lightnino/Projects/edp-lab')
INC = Path('/Users/lightnino/Projects/edp-lab-incident')
COMMIT = '787b473a78f5bcce814bafd8675ce1a9c5edea65'
OUT = ROOT / 'metadata/source_universes/approved_v1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(doc):
    return (json.dumps(doc, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode()


def main():
    evidence = {}

    def read(path, expected=None):
        raw = path.read_bytes()
        digest = sha(raw)
        if expected:
            assert digest == expected, str(path)
        evidence[str(path)] = digest
        return raw

    inventories = []
    for name, digest in [
        ('candidates-v1/whole_lab_inventory_v1.csv', '99f09213dc17d845a4ea6e97dfd6b99fabf7e4a7f5cb618253f7040fa706ca6c'),
        ('layout-v2/whole_lab_inventory_v2.csv', '1dcf16137a3a3cd0be3c4f025d9e6274e2a9bba34163e121004a97b1961bc45a'),
    ]:
        path = LAB / 'runs/whole_lab' / name
        rows = list(csv.DictReader(io.StringIO(read(path, digest).decode())))
        assert len(rows) == 3021
        assert len({r['inventory_id'] for r in rows}) == 3021
        assert all(r['inventory_id'] and r['final_path'] and re.fullmatch('[0-9a-f]{64}', r['sha256']) for r in rows)
        inventories.append((path, digest, rows))
    assert {(r['inventory_id'], r['sha256']) for r in inventories[0][2]} == {(r['inventory_id'], r['sha256']) for r in inventories[1][2]}
    indexed = {r['inventory_id']: r for r in inventories[1][2]}
    incident_path = 'docs/incidents/2026-10-21_source_universe_scope_control.md'
    incident = subprocess.check_output(['git', '-C', str(INC), 'show', f'{COMMIT}:{incident_path}'])
    assert 'QUALIFIED — OWNER_ATTESTED_PROVENANCE' in incident.decode()
    retained_path = INC / 'docs/incidents/2026-10-21_retained_raw_references.md'
    retained = read(retained_path).decode()
    outside = re.findall(r'^## (SRC\d+)\n.*?^- RAW SHA-256: `([0-9a-f]{64})`;', retained, re.M | re.S)
    assert len(outside) == len({i for i, _ in outside}) == 800
    assert not ({h for _, h in outside} & {r['sha256'] for r in indexed.values()})
    held = {'CFTC_COT', 'ECB_SDMX', 'NYC_TLC_TRIPS', 'ECB_REFERENCE_RATES'}
    policy_path = Path('/Users/lightnino/Projects/edp-lab-day3/scripts/prepare_n450.py')
    policy = read(policy_path).decode()
    assert 'HELD_OUT = {"CFTC_COT", "ECB_SDMX", "NYC_TLC_TRIPS", "ECB_REFERENCE_RATES"}' in policy
    holdouts = {r['inventory_id'] for r in indexed.values() if r['family'] in held}
    assert len(holdouts) == 41
    freeze = json.loads(read(ROOT / 'metadata/freezes/C300_v1/freeze.json', '7378b5d183cc4d45e0670eae6d501f204e62fdee02d8b345d9a910300d411835'))
    read(ROOT / 'metadata/freezes/C300_v1/references.json')
    authorization = json.loads(read(ROOT / 'metadata/freezes/C300_v1/authorization.json', freeze['files']['authorization.json']))
    roster = list(csv.DictReader(io.StringIO(read(ROOT / 'metadata/cohorts/C300.csv', freeze['files']['C300.csv']).decode())))
    # This original frozen manifest is used only for C300 compatibility, never universe authorization.
    frozen = list(csv.DictReader(io.StringIO(read(ROOT / 'metadata/corpus_manifest_v3.csv', freeze['files']['corpus_manifest_v3.csv']).decode())))
    registry = {r['source_instance_id']: r for r in frozen}
    packet = json.loads(read(LAB / 'runs/c300/frozen-v1/review.json', freeze['files']['review.json']))
    assert authorization['admit_and_freeze'] is True
    assert authorization['packet_sha256'] == freeze['files']['review.json']
    assert authorization['roster_sha256'] == freeze['files']['C300.csv']
    ids = {r['source_instance_id'] for r in roster}
    assert len(roster) == len(ids) == len(packet['members']) == 300
    assert ids == {m['source_instance_id'] for m in packet['members']}
    compatibility = []
    for m in packet['members']:
        i = m['delivery_id']
        r = indexed[i]
        registered = registry[m['source_instance_id']]
        assert r['sha256'] == m['raw_sha256'] == registered['raw_sha256']
        assert r['final_path'] == str(LAB / m['raw_path']) == str(LAB / registered['raw_path'])
        assert i not in holdouts and m['source_instance_id'] not in {s for s, _ in outside}
        compatibility.append({'source_instance_id': m['source_instance_id'], 'inventory_id': i, 'raw_sha256': r['sha256'], 'status': 'PASS'})
    members = []
    for i, r in sorted(indexed.items()):
        member = {'identity': i, 'raw_sha256': r['sha256'], 'raw_path': r['final_path'], 'holdout': i in holdouts}
        if i.startswith('LOCAL_SEC_BULK_'):
            member['qualification'] = {'disposition': 'QUALIFIED — OWNER_ATTESTED_PROVENANCE', 'original_download_receipt': 'UNAVAILABLE', 'independent_publisher_digest': 'UNAVAILABLE', 'independently_verified_publisher_provenance': False, 'source_instance_id': None}
        members.append(member)
    doc = {
        'schema': 'SOURCE_UNIVERSE_AUTHORITY_V1', 'universe_id': 'EDP_LAB_ORIGINAL_SOURCE_UNIVERSE', 'universe_version': '1',
        'member_count': 3021, 'inventory_reference': str(inventories[1][0]), 'inventory_sha256': inventories[1][1],
        'original_inventories': [{'path': str(p), 'sha256': h} for p, h, _ in inventories],
        'canonicalization': 'UTF-8; JSON keys sorted; separators comma/colon; ensure_ascii=false; one final LF; members sorted by inventory identity; SHA-256 over complete file bytes; digest external',
        'approval_reference': 'metadata/source_universes/approved_v1/owner_authorization.json',
        'holdout_policy': {'reference': str(policy_path), 'sha256': evidence[str(policy_path)], 'owner_instruction': 'Step 3 — Approved Source Universe v1, section 3', 'reserved_count': 41, 'development_cohorts': 'DENY'},
        'outside_universe_policy': {'count': 800, 'membership': 'EXCLUDED', 'retention': 'RETAIN; no deletion, modification or automatic admission', 'reference': str(retained_path), 'sha256': evidence[str(retained_path)]},
        'qualification_evidence': {'worktree': str(INC), 'commit': COMMIT, 'path': incident_path, 'sha256': sha(incident), 'section': '16', 'additional_owner_statement_reference': 'Current owner instruction: Step 3, section 2', 'owner_attestation': 'User-supplied Local ZIP — Downloaded Manually by Owner Directly from the Official SEC Website.', 'admission': 'Not executed; all other applicable mechanical and cohort authorization checks remain required'},
        'members': members,
    }
    raw = canonical(doc)
    digest = sha(raw)
    approval = {'status': 'PENDING', 'manifest_path': 'metadata/source_universes/approved_v1/manifest.json', 'manifest_sha256': digest, 'approved_by': None, 'authorized_at': None, 'owner_approval_evidence': None, 'authorization_text': None, 'note': 'Agent-prepared placeholder; no owner authorization of this digest has been recorded.'}
    report = {'assertion_author': 'AGENT', 'status': 'PASS', 'manifest_sha256': digest, 'checks': {'inventory_v1_count': 3021, 'inventory_v2_count': 3021, 'identity_hash_population_equal': True, 'identities_unambiguous': True, 'expected_hashes_well_formed': True, 'holdouts_in_universe': 41, 'outside_universe_excluded': 800, 'C300_identity_hash_matches': 300, 'C300_outside_overlap': 0, 'C300_holdout_overlap': 0, 'historical_frozen_hashes': 'PASS', 'original_inventory_hashes': 'PASS'}, 'evidence_sha256': evidence, 'c300_crosswalk': sorted(compatibility, key=lambda m: m['source_instance_id']), 'limits': 'Inventory expected hashes compared; RAW bytes not scanned. Historical retention references checked; no live local/remote 800-object integrity claim. No admission, IDs, freeze, activation or regression tests.'}
    # Recheck every evidence file after verification; never silently overwrite proposals.
    for path, expected in evidence.items():
        assert sha(Path(path).read_bytes()) == expected, path
    OUT.mkdir(parents=True, exist_ok=True)
    for name, content in [('manifest.json', raw), ('owner_authorization.json', canonical(approval)), ('verification.json', canonical(report)), ('manifest.sha256', f'{digest}  manifest.json\n'.encode())]:
        with (OUT / name).open('xb') as f:
            f.write(content)
    print(json.dumps({'manifest_sha256': digest, 'checks': report['checks']}, indent=2))


if __name__ == '__main__':
    main()
