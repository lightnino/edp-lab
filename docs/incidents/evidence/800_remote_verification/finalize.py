"""Compact newly generated evidence; never touches RAW or historical evidence."""
import csv, hashlib, json
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
rows=json.loads((OUT/'objects.json').read_text()); assert len(rows)==800
fields=['source_instance_id','presence','listed_bytes','size_match','listing_at','read_started_at','read_completed_at','method','read_bytes','read_size_match','current_sha256','hash_status','error']
with (OUT/'objects.csv').open('w',newline='') as stream:
 writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore',lineterminator='\n'); writer.writeheader(); writer.writerows(rows)
# Remove only redundant derived JSON representations produced in this task.
(OUT/'objects.json').unlink()
(OUT/'expected.json').unlink()
summary=json.loads((OUT/'summary.json').read_text())
listings=json.loads((OUT/'listings.json').read_text())
start=min(x['started_at'] for x in listings.values()); end=max(x['completed_at'] for x in listings.values())
read_start=min(r['read_started_at'] for r in rows); read_end=max(r['read_completed_at'] for r in rows)
exceptions=json.loads((OUT/'readback_exceptions.json').read_text()) if (OUT/'readback_exceptions.json').exists() else None
if exceptions:
 read_start=min([read_start]+[r['read_started_at'] for r in exceptions['first_attempts']])
counts={s:sum(r['hash_status']==s for r in rows) for s in ['HASH_MATCH','HASH_MISMATCH','HASH_NOT_CHECKED']}
result=f'''| Current result | Objects |
| --- | ---: |
| PRESENT | {sum(r['presence']=='PRESENT' for r in rows)} |
| MISSING | {sum(r['presence']=='MISSING' for r in rows)} |
| INACCESSIBLE | {sum(r['presence']=='INACCESSIBLE' for r in rows)} |
| Current listed size matches historical receipt | {sum(r['size_match'] for r in rows)} |
| HASH_MATCH (complete current readback) | {counts['HASH_MATCH']} |
| HASH_MISMATCH (complete current readback) | {counts['HASH_MISMATCH']} |
| HASH_NOT_CHECKED (complete-object integrity unverified) | {counts['HASH_NOT_CHECKED']} |

Current listed total and final complete-readback total: **{summary['listed_bytes']:,} bytes** and **{summary['read_bytes']:,} bytes**, respectively. Historical receipt total: **79,225,793 bytes**.

Captured listing interval (UTC): **{start}** through **{end}**. Readback interval, including the initial exception and isolated retry (UTC): **{read_start}** through **{read_end}**. Aggregate finalized at **{summary['completed_at']}**. Per-object timestamps are in `objects.csv`; first-attempt exception timestamps are retained in `readback_exceptions.json`.
'''
if exceptions:
 result+='\nInitial incomplete responses (a partial digest does not establish changed RAW):\n\n'
 for first in exceptions['first_attempts']:
  final=next(r for r in rows if r['source_instance_id']==first['source_instance_id'])
  result+=f"- `{first['source_instance_id']}`: first response **{first.get('read_bytes',0):,} / {first['expected_bytes']:,} bytes**; final isolated retry outcome **{final['hash_status']}**.\n"
 budget=sum(r['expected_bytes'] for r in exceptions['first_attempts'])
 extra=summary['first_attempt_partial_bytes']
 result+=f"\nThe initial verifier mechanically labeled incomplete-response digests HASH_MISMATCH; these observations are **HASH_NOT_CHECKED for full-object integrity**. The exact isolated retry budget of **{budget:,} bytes** was recorded before retries. Both attempts are retained in `readback_exceptions.json`. Actual payload read across all attempts: **{summary['payload_bytes_all_attempts']:,} bytes**, including **{extra:,}** extra partial-attempt bytes ({100*extra/79225793:.2f}% above the baseline). No broad readback was repeated.\n"
result+='\nFinal unverified objects: '+(', '.join(r['source_instance_id'] for r in rows if r['hash_status']=='HASH_NOT_CHECKED') or '**none**')+'.\n'
p=ROOT/'docs/incidents/2026-10-21_800_remote_verification.md'
s=p.read_text().replace('RESULTS_PLACEHOLDER',result)
# Seal all reproducibility inputs/outputs, excluding the seal and subsequent validation result.
digests={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.iterdir()) if p.is_file() and p.name not in ['artifact_digests.json','validation.json']}
(OUT/'artifact_digests.json').write_text(json.dumps(digests,indent=2,sort_keys=True)+'\n')
seal=hashlib.sha256((OUT/'artifact_digests.json').read_bytes()).hexdigest()
s=s.replace('DIGESTS_PLACEHOLDER',f"Evidence seal `artifact_digests.json` SHA-256: `{seal}`. Current per-instance `objects.csv` SHA-256: `{digests['objects.csv']}`. All other input/output digests are enumerated in the two digest files.")
p.write_text(s)
from validate import main
result=main()
(OUT/'validation.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
