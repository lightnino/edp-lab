"""Offline acquisition tests; synthetic publisher responses are never REAL evidence."""

import hashlib
import io
import json
from datetime import date, timedelta
from urllib.error import HTTPError
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from edp_lab.ingestion import c300_acquisition as acquisition


def documents():
    fsds = [f'{acquisition.BASE}/files/dera/data/financial-statement-data-sets/{y}q{q}.zip'
            for y in range(2011, 2026) for q in range(1, 5)]
    form13f = [f'{acquisition.BASE}/files/structureddata/data/form-13f-data-sets/'
               f'{y}q{q}_form13f.zip'
               for y in range(2013, 2024) for q in range(1, 5) if (y, q) >= (2013, 3)]
    docs = {url: ''.join(f'<a href="{link}">release</a>' for link in links).encode()
            for url, links in zip(acquisition.CATALOGS.values(), [fsds, form13f], strict=True)}
    days = [date(2023, 1, 1) + timedelta(days=i) for i in range(365)]
    for quarter, url in enumerate(acquisition.DIRECTORIES, 1):
        items = [{'name': f'master.{day:%Y%m%d}.idx'} for day in reversed(days)
                 if (day.month - 1) // 3 + 1 == quarter]
        items.append({'name': 'company.20230101.idx'})
        docs[url] = json.dumps({'directory': {'item': items}}).encode()
    return docs


class FixtureFetcher:
    def __init__(self, directory, docs):
        self.directory, self.docs, self.calls = directory, docs, []

    def fetch(self, url):
        self.calls.append(url)
        folder = self.directory / f'fixture-{len(self.calls)}'
        folder.mkdir()
        raw = self.docs[url]
        (folder / 'body').write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        receipt = {'status': 'COMPLETE', 'requested_url': url, 'final_url': url,
                   'sha256': digest, 'bytes': len(raw)}
        acquisition.write_new(folder / 'receipt.json', receipt)
        return {'body': str((folder / 'body').relative_to(self.directory)), 'sha256': digest,
                'receipt': str((folder / 'receipt.json').relative_to(self.directory)),
                'receipt_sha256': acquisition.sha256_file(folder / 'receipt.json')}


def prepared(tmp_path):
    fetcher = FixtureFetcher(tmp_path, documents())
    plan = acquisition.prepare(tmp_path, fetcher)
    return plan, fetcher


def zip_bytes():
    output = io.BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('sub.txt', b'adsh\n000001\n000001\n')
        archive.writestr('../opaque-name.txt', b'not extracted')
    return output.getvalue()


def test_exact_selection_uses_links_not_member_or_row_counts():
    docs = documents()
    candidates = acquisition.select_candidates(docs)
    assert len(candidates) == 300
    assert candidates[0]['filename'] == '2011q1.zip'
    assert candidates[59]['filename'] == '2025q4.zip'
    assert candidates[60]['filename'] == '2013q3_form13f.zip'
    assert candidates[101]['filename'] == '2023q4_form13f.zip'
    assert candidates[102]['filename'] == 'master.20230101.idx'
    assert candidates[-1]['filename'] == 'master.20230717.idx'
    assert len({c['url'] for c in candidates}) == 300
    assert all(c['source_instance_id'] is None for c in candidates)
    # Fixtures include weekends intentionally: discover publisher entries, not a calendar.
    docs[acquisition.CATALOGS['SEC_FSDS']] = b'<html>access denied</html>'
    with pytest.raises(ValueError, match='official catalog link'):
        acquisition.select_candidates(docs)


def test_missing_daily_entries_do_not_trigger_replacement():
    docs = documents()
    for url in acquisition.DIRECTORIES:
        docs[url] = b'{"directory":{"item":[]}}'
    with pytest.raises(ValueError, match='Fewer than 198'):
        acquisition.select_candidates(docs)


def test_prepare_reuses_and_verifies_retained_evidence(tmp_path):
    plan, fetcher = prepared(tmp_path)
    before = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert len(fetcher.calls) == 6
    assert acquisition.prepare(tmp_path, fetcher) == plan
    assert len(fetcher.calls) == 6
    assert {p: p.read_bytes() for p in before} == before
    report = acquisition.report(tmp_path)
    assert report['candidate_counts'] == acquisition.EXPECTED_COUNTS
    assert report['acquired_count'] == report['admitted_count'] == 0
    assert report['cohort_status'] == 'NOT_FROZEN'
    first = next(iter(plan['captures'].values()))
    (tmp_path / first['body']).write_bytes(b'changed')
    with pytest.raises(ValueError, match='Changed acquisition evidence'):
        acquisition.load_plan(tmp_path)
    assert len(fetcher.calls) == 6


def test_altered_plan_is_rejected_even_if_rehashed(tmp_path):
    plan, _ = prepared(tmp_path)
    plan['candidates'][0]['url'] = acquisition.BASE + '/invented.zip'
    plan['plan_sha256'] = acquisition.object_hash(
        {k: v for k, v in plan.items() if k != 'plan_sha256'})
    (tmp_path / 'candidates.json').write_bytes(acquisition.encoded(plan))
    with pytest.raises(ValueError, match='captured publisher evidence'):
        acquisition.load_plan(tmp_path)


def test_download_resume_hash_gate_and_no_extraction(tmp_path):
    plan, fetcher = prepared(tmp_path)
    for candidate in plan['candidates'][:2]:
        fetcher.docs[candidate['url']] = zip_bytes()
    acquisition.download(tmp_path, fetcher, limit=1)
    report = acquisition.report(tmp_path)
    assert report['acquired_count'] == 1
    assert report['admitted_count'] == 0
    assert not (tmp_path / 'sub.txt').exists()
    acquisition.download(tmp_path, fetcher, limit=1)
    assert len(fetcher.calls) == 8
    assert acquisition.report(tmp_path)['equal_hash_review_groups'] == [['CAND0001', 'CAND0002']]
    record = json.loads((tmp_path / 'payload-CAND0001.json').read_bytes())
    assert len(record['inspection']['members']) == 2  # archive remains one candidate
    (tmp_path / record['capture']['body']).write_bytes(b'changed delivery')
    with pytest.raises(ValueError, match='Changed acquisition evidence'):
        acquisition.download(tmp_path, fetcher, limit=1)
    assert len(fetcher.calls) == 8  # never silently refetch changed inputs


class Response(io.BytesIO):
    def __init__(self, raw, headers):
        super().__init__(raw)
        self.headers = headers
        self.status = 200
        self.url = acquisition.BASE + '/fixture'


@pytest.mark.parametrize('headers', [{'Content-Length': '999'}, {'Content-Encoding': 'gzip'}])
def test_http_integrity_failures_are_retained(tmp_path, headers):
    fetcher = acquisition.Fetcher(tmp_path, 'Fixture contact@example.invalid')
    fetcher.opener.open = lambda *args, **kwargs: Response(b'fixture', headers)
    with pytest.raises(ValueError, match='retained evidence'):
        fetcher.fetch(acquisition.BASE + '/fixture')
    receipt = json.loads(next(tmp_path.glob('attempts/*/receipt.json')).read_bytes())
    assert receipt['status'] == 'FAILED'
    assert receipt['error']


@pytest.mark.parametrize('code', [403, 429])
def test_access_denial_stops_without_retry_and_retains_body(tmp_path, code):
    fetcher = acquisition.Fetcher(tmp_path, 'Fixture contact@example.invalid')
    calls = []

    def denied(*args, **kwargs):
        calls.append(1)
        raise HTTPError(acquisition.BASE + '/fixture', code, 'denied', {},
                        io.BytesIO(b'<html>denied</html>'))

    fetcher.opener.open = denied
    with pytest.raises(ValueError, match='retained evidence'):
        fetcher.fetch(acquisition.BASE + '/fixture')
    assert len(calls) == 1
    assert next(tmp_path.glob('attempts/*/body')).read_bytes() == b'<html>denied</html>'


def test_retry_keeps_independent_attempts(tmp_path, monkeypatch):
    fetcher = acquisition.Fetcher(tmp_path, 'Fixture contact@example.invalid')
    calls = []
    monkeypatch.setattr(acquisition.time, 'sleep', lambda seconds: None)

    def response(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise HTTPError(acquisition.BASE + '/fixture', 503, 'unavailable', {},
                            io.BytesIO(b'unavailable'))
        return Response(b'fixture', {'Content-Length': '7'})

    fetcher.opener.open = response
    reference = fetcher.fetch(acquisition.BASE + '/fixture')
    assert len(list(tmp_path.glob('attempts/*/receipt.json'))) == 2
    assert acquisition.verified_capture(tmp_path, reference,
                                        acquisition.BASE + '/fixture').read_bytes() == b'fixture'


@pytest.mark.parametrize('url', ['http://www.sec.gov/x', 'https://evil.example/x',
                                'https://www.sec.gov@evil.example/x'])
def test_unofficial_urls_rejected_before_request(url, tmp_path):
    with pytest.raises(ValueError, match='publisher URL'):
        acquisition.Fetcher(tmp_path, 'Fixture contact@example.invalid').fetch(url)


def test_paths_and_contact(tmp_path):
    for relative in ['metadata', 'data/raw', 'runs/profiling']:
        with pytest.raises(ValueError, match='runs/c300'):
            acquisition.workspace(tmp_path, tmp_path / relative)
    with pytest.raises(ValueError, match='escapes'):
        acquisition.local_file(tmp_path, '../outside')
    with pytest.raises(ValueError, match='User-Agent'):
        acquisition.Fetcher(tmp_path, None)
    assert acquisition.workspace(tmp_path, tmp_path / 'runs/c300/test').is_dir()


def test_html_index_payload_is_not_validated_as_data(tmp_path):
    path = tmp_path / 'body'
    path.write_bytes(b'<!doctype html><html>denied</html>')
    with pytest.raises(ValueError, match='HTML'):
        acquisition.inspect_payload(path, 'master.20230103.idx')


def test_no_production_metadata_or_raw_writes(tmp_path):
    prepared(tmp_path)
    assert not (tmp_path / 'metadata').exists()
    assert not (tmp_path / 'data').exists()
    assert not any(p.name == 'C300.csv' for p in tmp_path.rglob('*'))
    assert not any(p.name == 'corpus_manifest.csv' for p in tmp_path.rglob('*'))


def test_offline_specification_is_idempotent_and_has_no_fabricated_sources(tmp_path):
    first = acquisition.prepare_specification(tmp_path)
    before = (tmp_path / 'acquisition-spec.json').read_bytes()
    assert acquisition.prepare_specification(tmp_path) == first
    assert (tmp_path / 'acquisition-spec.json').read_bytes() == before
    assert first['population'] == acquisition.EXPECTED_COUNTS
    assert first['authority_timestamp'] is None
    assert 'candidates' not in first
    assert not (tmp_path / 'candidates.json').exists()


def test_invalid_zip_retains_response_without_completed_payload(tmp_path):
    plan, fetcher = prepared(tmp_path)
    fetcher.docs[plan['candidates'][0]['url']] = b'<html>not a ZIP</html>'
    with pytest.raises(ValueError, match='inspection failed'):
        acquisition.download(tmp_path, fetcher, limit=1)
    failure = json.loads(next(tmp_path.glob('fixture-*/inspection-failure.json')).read_bytes())
    assert failure['candidate_id'] == 'CAND0001'
    assert acquisition.verified_capture(
        tmp_path, failure['capture'], plan['candidates'][0]['url']).read_bytes().startswith(b'<html>')
    assert acquisition.report(tmp_path)['acquired_count'] == 0
    assert not list(tmp_path.glob('payload-*.json'))
