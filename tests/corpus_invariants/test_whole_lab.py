"""Offline Whole Lab tests; synthetic responses never count as real acquisitions."""

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from edp_lab.ingestion import whole_lab
from edp_lab.ingestion.c300_acquisition import object_hash, write_new


class FakeFetcher:
    def __init__(self, directory, documents):
        self.directory = directory
        self.documents = documents
        self.blocked_hosts = set()
        self.calls = []

    def fetch(self, url):
        self.calls.append(url)
        if url not in self.documents:
            if 'sec.gov' in url:
                self.blocked_hosts.add('www.sec.gov')
            raise ValueError('synthetic publisher unavailable')
        folder = self.directory / f'fake-{len(self.calls)}'
        folder.mkdir()
        body = folder / 'body'
        body.write_bytes(self.documents[url])
        receipt = folder / 'receipt.json'
        receipt.write_text(json.dumps({'status': 'COMPLETE', 'requested_url': url,
                                       'bytes': body.stat().st_size,
                                       'sha256': hashlib.sha256(body.read_bytes()).hexdigest()}))
        return {'body': str(body.relative_to(self.directory)),
                'sha256': hashlib.sha256(body.read_bytes()).hexdigest(),
                'receipt': str(receipt.relative_to(self.directory)),
                'receipt_sha256': hashlib.sha256(receipt.read_bytes()).hexdigest()}


def test_discovery_continues_other_publishers_without_inventing_sec_deliveries(tmp_path):
    documents = {
        whole_lab.PAGES['ECB']: b'<a href="/stats/eurofxref/eurofxref-hist.zip">history</a>',
        whole_lab.PAGES['TREASURY']: b'Official synthetic documentation',
        whole_lab.PAGES['NASDAQ']: b'Official synthetic directory documentation',
        whole_lab.PAGES['NYC_TLC']: b'<a href="https://d37ci6vzurychx.cloudfront.net/'
                                  b'trip-data/yellow_tripdata_2025-01.parquet">January</a>',
    }
    fetcher = FakeFetcher(tmp_path, documents)
    plan = whole_lab.discover(tmp_path, fetcher)
    assert len(plan['candidates']) == 8  # 1 ECB, 5 Treasury, 1 Nasdaq, 1 TLC
    assert not any(c['publisher'] == 'SEC' for c in plan['candidates'])
    assert plan['requested_nested_sizes'] == [300, 700, 1500, 2000, 3000]
    assert plan['cohort_status'] == 'NOT_FROZEN'
    assert whole_lab.load_plan(tmp_path) == plan
    assert whole_lab.report(tmp_path)['verified_downloaded_deliveries'] == 0
    before = len(fetcher.calls)
    assert whole_lab.discover(tmp_path, fetcher) == plan
    assert len(fetcher.calls) == before


def test_mutated_discovery_evidence_blocks_replay(tmp_path):
    fetcher = FakeFetcher(tmp_path, {whole_lab.PAGES['NASDAQ']: b'documentation'})
    plan = whole_lab.discover(tmp_path, fetcher)
    capture = next(iter(plan['captures'].values()))
    (tmp_path / capture['body']).write_bytes(b'changed')
    with pytest.raises(ValueError, match='evidence changed'):
        whole_lab.load_plan(tmp_path)


def test_format_checks_reject_error_pages_and_empty_xml(tmp_path):
    body = tmp_path / 'body'
    body.write_bytes(b'<html>denied</html>')
    with pytest.raises(ValueError, match='HTML'):
        whole_lab.check_payload(body, {'publisher': 'SEC', 'filename': 'master.idx'})
    body.write_bytes(b'<feed xmlns="http://www.w3.org/2005/Atom"/>')
    with pytest.raises(ValueError, match='no published entries'):
        whole_lab.check_payload(body, {'publisher': 'TREASURY', 'filename': 'xml'})
    body.write_bytes(b'PAR1contentPAR1')
    assert whole_lab.check_payload(body, {'publisher': 'NYC_TLC', 'filename': 'file.parquet'})
    body.write_bytes(b'PAR1contentFAIL')
    with pytest.raises(ValueError, match='Parquet'):
        whole_lab.check_payload(body, {'publisher': 'NYC_TLC', 'filename': 'file.parquet'})


def test_local_available_delivery_is_not_downloaded(tmp_path):
    local = tmp_path / 'local.txt'
    local.write_bytes(b'already available')
    candidate = {'candidate_id': 'test', 'url': 'https://www.sec.gov/fixture.idx',
                 'family': 'EXISTING', 'edition': '2025Q1', 'publisher': 'SEC', 'filename': 'a.idx'}
    plan = {'version': whole_lab.VERSION, 'captures': {}, 'candidates': [candidate],
            'failures': [], 'requested_nested_sizes': [300, 700, 1500, 2000, 3000]}
    plan['plan_sha256'] = object_hash(plan)
    write_new(tmp_path / 'candidates.json', plan)
    inventory = {'datasets': [{'dataset_id': 'local', 'family': 'EXISTING',
                              'edition_label': '2025Q1', 'representations': [{
                                  'kind': 'FILE', 'availability': 'VERIFIED', 'path': str(local),
                                  'bytes': local.stat().st_size,
                                  'sha256': hashlib.sha256(local.read_bytes()).hexdigest()}]}]}
    fetcher = FakeFetcher(tmp_path, {})
    whole_lab.download(tmp_path, fetcher, inventory, 1)
    assert fetcher.calls == []
    failure = json.loads(next(tmp_path.glob('failure-*/failure.json')).read_bytes())
    assert 'no duplicate download' in failure['error']
    assert not list(tmp_path.glob('delivery-*.json'))


def test_only_expected_publisher_hosts_are_requested():
    with pytest.raises(ValueError, match='publisher host'):
        whole_lab.checked_url('https://unexpected.example/dataset.zip')


def test_no_source_or_cohort_writes(tmp_path):
    whole_lab.discover(tmp_path, FakeFetcher(tmp_path, {}))
    assert not (tmp_path / 'metadata').exists()
    assert not list(tmp_path.rglob('C300.csv'))
    assert not list(tmp_path.rglob('corpus_manifest.csv'))


def test_http_200_partial_transfer_is_retained_and_retried(tmp_path, monkeypatch):
    calls = []
    url = 'https://www.sec.gov/fixture.idx'
    monkeypatch.setattr(whole_lab.time, 'sleep', lambda seconds: None)

    def curl(arguments, **kwargs):
        calls.append(arguments)
        body = tmp_path / arguments[arguments.index('--output') + 1]
        raw = b'partial' if len(calls) == 1 else b'complete response'
        body.write_bytes(raw)
        return subprocess.CompletedProcess(arguments, 28 if len(calls) == 1 else 0,
                                           json.dumps({'http_code': 200, 'size_download': len(raw),
                                                       'url_effective': url}), '')

    monkeypatch.setattr(whole_lab.subprocess, 'run', curl)
    fetcher = whole_lab.CurlFetcher(tmp_path, 'Fixture contact@example.invalid')
    reference = fetcher.fetch(url)
    assert len(calls) == 2
    assert all('--http1.1' in call and '--insecure' not in call for call in calls)
    assert whole_lab.capture_body(tmp_path, reference, url).read_bytes() == b'complete response'
    statuses = [json.loads(p.read_bytes())['status']
                for p in tmp_path.glob('attempts/*/receipt.json')]
    assert sorted(statuses) == ['COMPLETE', 'FAILED']
    with pytest.raises(ValueError, match='association mismatch'):
        whole_lab.capture_body(tmp_path, reference, 'https://www.sec.gov/another.idx')


def test_review_packet_does_not_claim_missing_sources_or_completed_cohorts(tmp_path):
    whole_lab.discover(tmp_path, FakeFetcher(tmp_path, {}))
    availability = tmp_path / 'availability.json'
    write_new(availability, {'version': 'LOCAL_SOURCE_AVAILABILITY_V1', 'datasets': []})
    summary = whole_lab.review_packet(tmp_path, availability)
    assert summary['verified_candidates_without_equal_hash_review'] == 0
    assert summary['existing_local_datasets'] == 0
    assert set(summary['selection_readiness'].values()) == {'BLOCKED'}
    with open(summary['review_inventory']) as stream:
        packet = json.load(stream)
    assert packet['existing_admitted_gold_instances'] == 0
    assert packet['new_admissions'] == packet['frozen_cohorts_created'] == 0


@pytest.mark.parametrize("legacy_layout", [False, True])
def test_organized_bytes_keep_original_receipts_and_resume_offline(
        tmp_path, monkeypatch, legacy_layout):
    monkeypatch.chdir(tmp_path)
    directory = tmp_path / 'runs/whole_lab/test'
    directory.mkdir(parents=True)
    candidate = {'candidate_id': 'fixture', 'publisher': 'SEC', 'filename': 'master.idx',
                 'url': 'https://www.sec.gov/fixture.idx', 'family': 'DAILY', 'edition': 'fixture'}
    plan = {'version': whole_lab.VERSION, 'captures': {}, 'failures': [],
            'candidates': [candidate], 'requested_nested_sizes': [300]}
    plan['plan_sha256'] = object_hash(plan)
    write_new(directory / 'candidates.json', plan)
    fetcher = FakeFetcher(directory, {candidate['url']: b'publisher source bytes'})
    capture = fetcher.fetch(candidate['url'])
    write_new(directory / 'delivery-fixture.json', {
        'plan_sha256': plan['plan_sha256'], 'candidate': candidate, 'capture': capture})
    receipt_before = (directory / capture['receipt']).read_bytes()

    def move(source, target, **kwargs):
        assert not target.exists()
        Path(source).rename(target)

    legacy_bytes = None
    if legacy_layout:
        old = (tmp_path / 'data/raw/whole_lab/sec' /
               whole_lab.delivery_candidate_id(plan, candidate, capture) / 'master.idx')
        old.parent.mkdir(parents=True)
        (directory / capture['body']).rename(old)
        audits = directory / 'relocations'
        audits.mkdir()
        legacy = audits / f"{object_hash(capture['body'])}.json"
        write_new(legacy, {'original_body': capture['body'], 'final_path': str(old),
                           'sha256': capture['sha256']})
        legacy_bytes = legacy.read_bytes()

    monkeypatch.setattr(whole_lab, 'move_existing', move)
    collision = whole_lab.canonical_delivery_path(plan, candidate, capture)
    collision.parent.mkdir(parents=True, exist_ok=True)
    collision.write_bytes(b'preexisting unrelated bytes')
    with pytest.raises(ValueError, match='destination already exists'):
        whole_lab.organize_acquired(directory)
    assert collision.read_bytes() == b'preexisting unrelated bytes'
    collision.unlink()
    assert whole_lab.organize_acquired(directory)['organized_verified_deliveries'] == 1
    result = whole_lab.capture_body(directory, capture)
    assert result.is_relative_to(tmp_path / 'data/raw/sec/daily')
    if legacy_layout:
        assert not old.exists()
        assert legacy.read_bytes() == legacy_bytes
    assert not (directory / capture['body']).exists()
    assert whole_lab.capture_body(directory, capture).read_bytes() == b'publisher source bytes'
    assert (directory / capture['receipt']).read_bytes() == receipt_before
    assert whole_lab.organize_acquired(directory)['organized_verified_deliveries'] == 1
    assert whole_lab.report(directory)['verified_downloaded_deliveries'] == 1
    inventory = whole_lab.corpus_availability({
        'version': 'LOCAL_SOURCE_AVAILABILITY_V1', 'datasets': []})
    assert len(inventory['datasets']) == 1
    with pytest.raises(ValueError, match='no duplicate download'):
        whole_lab.local_match(candidate, inventory)

    # A separately retained changed delivery of the same URL gets another RAW path.
    second = tmp_path / 'runs/whole_lab/test2'
    second.mkdir()
    write_new(second / 'candidates.json', plan)
    new_capture = FakeFetcher(second, {candidate['url']: b'updated publisher bytes'}).fetch(
        candidate['url'])
    write_new(second / 'delivery-fixture.json', {
        'plan_sha256': plan['plan_sha256'], 'candidate': candidate, 'capture': new_capture})
    whole_lab.organize_acquired(second)
    assert whole_lab.capture_body(directory, capture).read_bytes() == b'publisher source bytes'
    assert whole_lab.capture_body(second, new_capture).read_bytes() == b'updated publisher bytes'
    assert whole_lab.capture_body(directory, capture) != whole_lab.capture_body(second, new_capture)
    inventory = whole_lab.corpus_availability({
        'version': 'LOCAL_SOURCE_AVAILABILITY_V1', 'datasets': []})
    selected = whole_lab.local_match({**candidate, 'expected_sha256': new_capture['sha256']},
                                    inventory)
    assert Path(selected['representation']['path']).read_bytes() == b'updated publisher bytes'

    # Audits cannot redirect a verified delivery to another path.
    audit_path = directory / 'publisher-relocations' / f"{object_hash(capture['body'])}.json"
    audit = json.loads(audit_path.read_bytes())
    audit['final_path'] = str(tmp_path / 'outside.idx')
    audit_path.write_text(json.dumps(audit))
    with pytest.raises(ValueError, match='Invalid publisher relocation audit'):
        whole_lab.capture_body(directory, capture)
