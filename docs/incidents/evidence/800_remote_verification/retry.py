"""One bounded retry of incomplete/error responses; retain the first observation."""
import configparser, hashlib, json, subprocess, urllib.request, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
OUT=Path(__file__).resolve().parent
now=lambda:datetime.now(timezone.utc).isoformat()
def save(n,d): (OUT/n).write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def main():
 assert not (OUT/'readback_exceptions.json').exists(), 'Do not repeat a completed retry'
 rows=json.loads((OUT/'objects.json').read_text()); assert len(rows)==800
 failed=[r for r in rows if r['hash_status']!='HASH_MATCH']
 # At most 2 MB retry budget; unexpected retry scope stops before network reads.
 budget=sum(r['expected_bytes'] for r in failed)
 assert budget<=2000000, 'STOP: retry budget exceeds 2 MB'
 save('retry_preflight.json',dict(at=now(),objects=[r['source_instance_id'] for r in failed],max_payload_bytes=budget,reason='First response incomplete/error; bounded isolated retry'))
 original=[dict(r) for r in failed]
 config=configparser.ConfigParser(); config.read(Path.home()/'.databrickscfg')
 host=config['edp-lab']['host'].rstrip('/')
 token=json.loads(subprocess.check_output(['databricks','auth','token','-p','edp-lab','-o','json'],text=True))['access_token']
 for r in failed:
  r.update(read_started_at=now(),hash_status='HASH_NOT_CHECKED',method='UC Files API GET exact path; bounded streaming SHA-256; isolated retry after incomplete response')
  r.pop('error',None)
  req=urllib.request.Request(host+'/api/2.0/fs/files'+urllib.parse.quote(r['remote'].removeprefix('dbfs:'),safe='/'),headers={'Authorization':'Bearer '+token})
  try:
   h=hashlib.sha256(); count=0
   with urllib.request.urlopen(req,timeout=60) as response:
    r['response_status']=response.status
    r['response_content_length']=response.headers.get('Content-Length')
    length=r['response_content_length']
    if length is not None and int(length)!=r['expected_bytes']: raise ValueError('Content-Length mismatch')
    while count<r['expected_bytes']:
     chunk=response.read(min(65536,r['expected_bytes']-count))
     if not chunk: break
     h.update(chunk); count+=len(chunk)
   r.update(read_bytes=count,current_sha256=h.hexdigest(),read_size_match=count==r['expected_bytes'])
   r['hash_status']=('HASH_MATCH' if h.hexdigest()==r['expected_sha256'] else 'HASH_MISMATCH') if r['read_size_match'] else 'HASH_NOT_CHECKED'
  except Exception as exc: r['error']=type(exc).__name__+': '+str(exc)
  r['read_completed_at']=now()
 save('readback_exceptions.json',dict(first_attempts=original,retries=[dict(r) for r in failed],interpretation='Incomplete response is HASH_NOT_CHECKED for full-object integrity, even though initial verifier labels partial digest HASH_MISMATCH. Both observations retained.'))
 save('objects.json',rows)
 summary=json.loads((OUT/'summary.json').read_text())
 from collections import Counter
 summary.update(completed_at=now(),hashes=dict(Counter(r['hash_status'] for r in rows)),read_bytes=sum(r.get('read_bytes',0) for r in rows),retry_objects=len(failed),first_attempt_partial_bytes=sum(r.get('read_bytes',0) for r in original))
 summary['payload_bytes_all_attempts']=summary['read_bytes']+summary['first_attempt_partial_bytes']
 save('summary.json',summary)
 print(json.dumps(summary))
if __name__=='__main__':main()
