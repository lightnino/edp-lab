"""Offline evidence acceptance checks. Does not contact Databricks or read RAW."""
import collections, csv, hashlib, json
from pathlib import Path
from datetime import datetime
from verify import reconstruct
OUT=Path(__file__).resolve().parent

def main():
 summary=json.loads((OUT/'summary.json').read_text())
 rows=list(csv.DictReader((OUT/'objects.csv').open()))
 expected={r['source_instance_id']:r for r in reconstruct()}
 for r in rows:
  e=expected[r['source_instance_id']]
  if r['hash_status']=='HASH_MATCH': assert r['current_sha256']==e['expected_sha256'] and int(r['read_bytes'])==e['expected_bytes']
  elif r['hash_status']=='HASH_MISMATCH': assert r['read_size_match']=='True' and r['current_sha256']!=e['expected_sha256']
  else: assert r['hash_status']=='HASH_NOT_CHECKED' and (r.get('error') or r['read_size_match']!='True')
 assert len(rows)==len({r['source_instance_id'] for r in rows})==800
 assert collections.Counter(r['presence'] for r in rows)=={'PRESENT':800}
 counts=collections.Counter(r['hash_status'] for r in rows)
 assert dict(counts)==summary['hashes']
 assert all(r['size_match']=='True' for r in rows)
 assert sum(int(r['listed_bytes']) for r in rows)==79225793
 assert sum(int(r['read_bytes'] or 0) for r in rows)==summary['read_bytes']
 assert summary['size_matches']==800
 for r in rows:
  assert len(r['current_sha256'])==64
  assert datetime.fromisoformat(r['listing_at'])<=datetime.fromisoformat(r['read_started_at'])<=datetime.fromisoformat(r['read_completed_at'])
 exclusions=json.loads((OUT/'exclusions.json').read_text())
 assert {r['source_instance_id'] for r in rows}=={r['source_instance_id'] for r in exclusions['objects']}
 assert all(all(v for k,v in r.items() if k!='source_instance_id') for r in exclusions['objects'])
 assert len(exclusions['holdouts'])==41
 assert all(r['c300_identity_absent'] and r['c300_hash_absent'] for r in exclusions['holdouts'])
 inputs=json.loads((OUT/'input_digests.json').read_text())
 for path,digest in inputs.items(): assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest, path
 consumers=json.loads((OUT/'known_c300_consumers.json').read_text())
 assert consumers['physical_count']==300 and consumers['retained_800_intersection']==0
 for name,digest in json.loads((OUT/'artifact_digests.json').read_text()).items():
  assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==digest,name
 result=dict(status='PASS',objects=800,present=800,size_match=800,hash_match=counts.get('HASH_MATCH',0),hash_mismatch=counts.get('HASH_MISMATCH',0),hash_not_checked=counts.get('HASH_NOT_CHECKED',0),integrity_status='PASS' if counts.get('HASH_MATCH')==800 else 'FINDINGS',bytes=79225793,universe_excluded=800,c300_excluded=800,holdouts_excluded=41,checks='Unique coverage, current-byte hashes, byte sums, timestamp order, exclusions, input hashes, artifact hashes')
 print(json.dumps(result,sort_keys=True))
 return result
if __name__=='__main__': main()
