"""Read-only exception diagnosis. Counterfactual codecs never activate a parser."""
import importlib.util
import io
import json
from collections import Counter
from pathlib import Path

from edp_lab.ingestion.c300_admission import encoded
from edp_lab.ingestion.universe import sha
from edp_lab.parsers.c300_reader_v1 import RecordOccurrence
from edp_lab.parsers.c300_v1 import DAILY_HEADER, inspect_stream

ROOT = Path(__file__).resolve().parents[1]
LAB = Path('/Users/lightnino/Projects/edp-lab')
NATIVE_MANIFEST = 'runs/c300-m1/main_recovery_20261021_v4/collected-full/profile_run_manifest.json'
NATIVE_CODE = 'src/edp_lab/materialization/c300_m1.py'
SID = 'SRC010128'
RAW_SHA = '5869c2d2e76ec56302291d7812add9d8cc1a0b9788478050344e40d14927e71d'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def retained_native():
    baseline = json.loads((ROOT / 'metadata/baselines/O_C300_M1.json').read_bytes())
    manifest_raw = (LAB / NATIVE_MANIFEST).read_bytes()
    require(sha(manifest_raw) == baseline['retained_input_manifests'][NATIVE_MANIFEST]['sha256'],
            'NATIVE_RUNTIME_MANIFEST_CHANGED')
    contract = json.loads(manifest_raw)['contract']
    path = LAB / NATIVE_CODE
    require(sha(path.read_bytes()) == contract['code_sha256'][NATIVE_CODE],
            'NATIVE_M1_CODE_CHANGED')
    spec = importlib.util.spec_from_file_location('retained_native_m1', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, {'manifest': str(LAB / NATIVE_MANIFEST), 'manifest_sha256': sha(manifest_raw),
                    'code': str(path), 'code_sha256': sha(path.read_bytes())}


def inspect_bytes(raw):
    errors, widths, endings = [], Counter(), Counter()
    offset = 0
    rebuilt = {codec: bytearray() for codec in ('latin-1', 'cp1252')}
    representations_equal = True
    rows = number = 0
    for number, line in enumerate(io.BytesIO(raw), 1):
        content = line.removesuffix(b'\n').removesuffix(b'\r')
        ending = line[len(content):]
        endings['CRLF' if line.endswith(b'\r\n') else 'LF' if line.endswith(b'\n')
                else 'UNTERMINATED'] += 1
        if number > 7:
            widths[len(content.split(b'|'))] += 1
            rows += 1
        position = 0
        while position < len(content):
            try:
                content[position:].decode('utf-8', errors='strict')
                break
            except UnicodeDecodeError as exc:
                start, stop = position+exc.start, position+exc.end
                errors.append({'line': number, 'line_start': offset, 'record_bytes': len(line),
                    'record_sha256': sha(line), 'invalid_record_offset': start,
                    'invalid_absolute_offset': offset+start, 'invalid_hex': content[start:stop].hex(),
                    'following_hex': content[stop:stop+4].hex(),
                    'bounded_context_hex': content[max(0, start-16):min(len(content), stop+16)].hex(),
                    'field_ordinal': content[:start].count(b'|')+1, 'reason': exc.reason})
                position = stop
        # Counterfactual bijections only: no claim about publisher character intent.
        texts = [content.decode(codec, errors='strict') for codec in rebuilt]
        representations_equal &= texts[0] == texts[1]
        for codec, text in zip(rebuilt, texts, strict=True):
            rebuilt[codec].extend(text.encode(codec, errors='strict') + ending)
        offset += len(line)
    return {'raw_sha256': sha(raw), 'bytes': len(raw), 'physical_records': number,
            'data_records': rows, 'field_positions': sum(w*n for w, n in widths.items()),
            'data_widths': dict(widths), 'line_terminators': dict(endings),
            'non_ascii_byte_histogram': {f'{v:02x}': n for v, n in Counter(raw).items() if v >= 128},
            'all_utf8_errors': errors,
            'counterfactual_codecs': {'status': 'DIAGNOSTIC_ONLY_NOT_ADOPTED',
                'reconstructed_hashes': {codec: sha(bytes(b)) for codec, b in rebuilt.items()},
                'same_unicode_on_observed_repertoire': representations_equal,
                'source_charset_and_character_meaning': 'UNRESOLVED'}}


def native_fixture_check(native, directory, *, invalid):
    """Exercise the actual retained native M1 value oracle using synthetic data only."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    framing = ('Description: fixture\nLast Data Received: fixture\nComments: fixture\n'
               'Anonymous FTP: fixture\n \n' + DAILY_HEADER + '\n' + '-'*80 + '\n').encode()
    value = b'carrier\xc3O' if invalid else 'literal 日本'.encode()
    record = b'000123|' + value + b'|13F-HR/A|2012-01-04|edgar/fixture.txt\n'
    raw = framing + record + record
    source = directory / 'fixture.idx'
    source.write_bytes(raw)
    inspection = inspect_stream(io.BytesIO(raw), 'SEC_EDGAR_DAILY_MASTER')
    binding = {'source_instance_id': 'SYNTHETIC_NATIVE_COMPATIBILITY_FIXTURE',
               'source_family': 'SEC_EDGAR_DAILY_MASTER', 'raw_path': str(source),
               'raw_sha256': sha(raw), 'archive_member': '', 'member_sha256': sha(raw),
               'uncompressed_bytes': len(raw), 'expected_header': DAILY_HEADER.split('|'),
               'prefix_evidence': inspection['prefix_evidence']}
    packaged, offset = [], 0
    for number, line in enumerate(io.BytesIO(raw), 1):
        kind = 'HEADER' if number == 6 else 'METADATA' if number <= 7 else 'DATA'
        text = line.removesuffix(b'\n').decode('latin-1' if invalid else 'utf-8', errors='strict')
        occurrence = RecordOccurrence(binding['source_instance_id'], '', number, offset,
                                      line, tuple(text.split('|')), kind)
        packaged.append(native.package_record('DIAGNOSTIC_FIXTURE', binding, occurrence))
        offset += len(line)
    parquet = directory / 'fixture.parquet'
    pq.write_table(pa.Table.from_pylist(packaged, schema=native.record_schema()), parquet)
    return native.verify_parquet(directory, binding, parquet)


def main():
    import tempfile

    from observe_n450_b1 import scope

    rows, physical, _ = scope()
    row = next(r for r in rows if r['source_instance_id'] == SID)
    member = next(p for p in physical if p['raw_path'] == row['raw_path'])
    raw = Path(row['raw_path']).read_bytes()
    require(sha(raw) == RAW_SHA == row['raw_sha256'] and len(raw) == member['bytes'],
            'RAW_IDENTITY_OR_HASH_CHANGED')
    result = inspect_bytes(raw)
    receipt_path = Path(member['receipt_path'])
    receipt_raw = receipt_path.read_bytes()
    require(sha(receipt_raw) == member['receipt_sha256'], 'SOURCE_RECEIPT_CHANGED')
    receipt = json.loads(receipt_raw)
    native, native_ref = retained_native()
    with tempfile.TemporaryDirectory(prefix='m1-encoding-fixtures-') as temp:
        good = Path(temp) / 'good'
        good.mkdir()
        good_result = native_fixture_check(native, good, invalid=False)
        bad = Path(temp) / 'bad'
        bad.mkdir()
        try:
            native_fixture_check(native, bad, invalid=True)
        except UnicodeDecodeError as exc:
            candidate = {'status': 'REJECTED_BY_UNCHANGED_M1_VALUE_ORACLE', 'error': str(exc)}
        else:
            raise ValueError('UNEXPECTED_NATIVE_ACCEPTANCE_OF_BYTE_CARRIER')
    # Reuse every other source fingerprint, not its RAW scan.
    old = json.loads((ROOT / 'runs/n450/b1-v1/summary.json').read_bytes())
    reused = [r for r in old['results'] if r['source_instance_id'] != SID]
    require(len(reused) == 449 and all(sha((ROOT/r['reference']).read_bytes()) == r['sha256']
                                     for r in reused), 'UNCHANGED_POPULATION_EVIDENCE_CHANGED')
    result.update(source_instance_id=SID, source_identity=member['source_identity'],
        raw_path=row['raw_path'], original_failure_preserved='metadata/evaluations/n450_b1_v1.json',
        acquisition={'receipt': str(receipt_path), 'sha256': sha(receipt_raw),
                     'content_type': receipt['transfer'].get('content_type'),
                     'url': receipt['requested_url'], 'charset_attestation': 'NOT_PRESENT'},
        native_contract=native_ref, native_utf8_control=good_result,
        native_counterfactual_byte_carrier=candidate,
        source_status='HOLD', b1_classification='HUMAN_UNRESOLVED', eligible_n450=449,
        existing_449_evidence_reused=True, existing_449_raw_replayed=False,
        selected_policy='UNCHANGED_STRICT_UTF8; no evidence-supported new text profile adopted',
        remaining_decision='Provide an authoritative source charset/character interpretation, or explicitly '
          'approve a versioned opaque-byte transport value contract and its native verifier policy. '
          'Current M1 DIRECT_MAP strict UTF-8 text contract does not silently permit that substitution.',
        m2_implemented=False, parser_or_authorization_code_changed=False,
        raw_unchanged=sha(Path(row['raw_path']).read_bytes()) == RAW_SHA)
    out = ROOT / 'runs/n450/src010128-encoding-v1/diagnosis.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('xb') as handle:
        handle.write(encoded(result))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
