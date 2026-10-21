"""Read-only exact-path verification. No remote mutation or compute endpoints."""
import collections, concurrent.futures, csv, hashlib, json, re, subprocess, urllib.request, urllib.error, configparser
from datetime import datetime, timezone
from pathlib import Path
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
def now(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name, value): (OUT/name).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
def cli(*args): return subprocess.check_output(['databricks',*args,'-p','edp-lab','-o','json'], text=True)
def reconstruct():
    appendix = ROOT/'docs/incidents/2026-10-21_retained_raw_references.md'
    rows=[]
    for block in appendix.read_text().split('\n## ')[1:]:
        sid=block.splitlines()[0]
        family, candidate=re.search(r'Family: `([^`]+)`; candidate: `([^`]+)`',block).groups()
        digest, size=re.search(r'RAW SHA-256: `([^`]+)`; retained receipt bytes: (\d+)',block).groups()
        remote=re.search(r'- Remote: `([^`]+)`',block)[1]
        receipt, receipt_sha=re.search(r'- Remote receipt: `([^`]+)`; SHA-256 `([^`]+)`',block).groups()
        assert sha(receipt)==receipt_sha
        r=json.loads(Path(receipt).read_bytes())
        assert (r['source_instance_id'],r['remote'],r['sha256'],r['bytes'])==(sid,remote,digest,int(size))
        rows.append(dict(source_instance_id=sid,family=family,candidate=candidate,expected_sha256=digest,expected_bytes=int(size),remote=remote,receipt=receipt,receipt_sha256=receipt_sha))
    assert len(rows)==len({r['remote'] for r in rows})==800
    assert sum(r['expected_bytes'] for r in rows)==79225793
    assert sorted(collections.Counter(r['family'] for r in rows).values())==[100,300,400]
    return rows

def main():
    rows=reconstruct(); save('expected.json',rows)
    prefixes=sorted({r['remote'].rsplit('/',1)[0] for r in rows})
    listings=json.loads((OUT/'listings.json').read_text()) if (OUT/'listings.json').exists() else {}
    for prefix in prefixes:
        if prefix in listings: continue
        start=now(); entries=json.loads(cli('fs','ls',prefix)); end=now()
        # Retain only in-scope entries; never read unrelated objects.
        expected={r['remote'].rsplit('/',1)[1] for r in rows if r['remote'].startswith(prefix+'/')}
        listings[prefix]=dict(started_at=start,completed_at=end,entries=[e for e in entries if e['name'] in expected])
    save('listings.json',listings)
    for r in rows:
        prefix,name=r['remote'].rsplit('/',1)
        entry=next((e for e in listings[prefix]['entries'] if e['name']==name),None)
        r.update(presence='PRESENT' if entry and not entry['is_directory'] else 'MISSING',listed_bytes=entry['size'] if entry else None,listing_at=listings[prefix]['completed_at'])
        r['size_match']=r['listed_bytes']==r['expected_bytes']
    total=sum(r['listed_bytes'] or 0 for r in rows)
    save('preflight.json',dict(at=now(),expected_objects=800,expected_bytes=79225793,current_listed_bytes=total,all_sizes_match=all(r['size_match'] for r in rows),read_cap_bytes=79225793))
    assert all(r['size_match'] for r in rows), 'STOP: unexpected sizes; no bulk readback'
    print(json.dumps(dict(stage='PREFLIGHT_PASS',objects=800,bytes=total)),flush=True)
    config=configparser.ConfigParser(); config.read(Path.home()/'.databrickscfg')
    host=config['edp-lab']['host'].rstrip('/')
    token=json.loads(cli('auth','token'))['access_token']
    def verify(r):
        r.update(read_started_at=now(),method='UC Files API GET exact path; bounded streaming SHA-256; no scratch RAW',hash_status='HASH_NOT_CHECKED')
        try:
            path=r['remote'].removeprefix('dbfs:')
            request=urllib.request.Request(host+'/api/2.0/fs/files'+urllib.parse.quote(path,safe='/'),headers={'Authorization':'Bearer '+token})
            h=hashlib.sha256(); count=0
            with urllib.request.urlopen(request,timeout=60) as response:
                length=response.headers.get('Content-Length')
                if length is not None and int(length)!=r['expected_bytes']: raise ValueError('Content-Length differs from preflight')
                while count<r['expected_bytes']:
                    chunk=response.read(min(65536,r['expected_bytes']-count))
                    if not chunk: break
                    count+=len(chunk); h.update(chunk)
                # Content-Length bounds completeness; without it, at most one extra byte.
                extra=b'' if length is not None else response.read(1)
            r.update(read_bytes=count,current_sha256=h.hexdigest(),read_size_match=count==r['expected_bytes'] and not extra)
            r['hash_status']='HASH_MATCH' if r['read_size_match'] and h.hexdigest()==r['expected_sha256'] else 'HASH_MISMATCH'
        except Exception as exc:
            r['error']=type(exc).__name__+': '+str(exc)
            if isinstance(exc,urllib.error.HTTPError): r['read_http_status']=exc.code
        r['read_completed_at']=now()
        return r
    done=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for r in pool.map(verify,rows):
            done.append(r)
            if len(done)%50==0:
                save('objects.json',done); print(json.dumps(dict(completed=len(done),hashes=dict(collections.Counter(r['hash_status'] for r in done)))),flush=True)
    save('objects.json',done)
    save('summary.json',dict(completed_at=now(),objects=len(done),presence=dict(collections.Counter(r['presence'] for r in done)),size_matches=sum(r['size_match'] for r in done),hashes=dict(collections.Counter(r['hash_status'] for r in done)),listed_bytes=total,read_bytes=sum(r.get('read_bytes',0) for r in done)))
if __name__=='__main__': main()
