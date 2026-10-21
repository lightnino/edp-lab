"""Mechanical identity/hash exclusions and bounded historical dependency audit."""
import csv, hashlib, json, subprocess
from pathlib import Path
from datetime import datetime, timezone
OUT=Path(__file__).resolve().parent; ROOT=OUT.parents[3]; LAB=Path('/Users/lightnino/Projects/edp-lab'); SCOPE=Path('/Users/lightnino/Projects/edp-lab-scope-gate')
inputs={}
def load(p):
 p=Path(p); b=p.read_bytes(); inputs[str(p)]=hashlib.sha256(b).hexdigest(); return json.loads(b)
def table(p):
 p=Path(p); inputs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest(); return list(csv.DictReader(p.open()))
def save(n,d): (OUT/n).write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
from verify import reconstruct
rows=reconstruct()
for name in ['2026-10-21_retained_raw_references.md','2026-10-21_evidence_index.md','2026-10-21_source_universe_scope_control.md']:
 p=ROOT/'docs/incidents'/name; inputs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
index=(ROOT/'docs/incidents/2026-10-21_evidence_index.md').read_text()
assert all('`'+r['receipt']+'` | `'+r['receipt_sha256']+'`' in index for r in rows)

u=load(SCOPE/'metadata/source_universes/approved_v1/manifest.json')
assert inputs[str(SCOPE/'metadata/source_universes/approved_v1/manifest.json')]=='2198f9bad9c864bf339eff515992526e22efc4230160614a8f86daf3143f463c'
commit='319281c17d957dc8d442aaa63278df0d5a1596b3'
committed=subprocess.check_output(['git','-C',str(SCOPE),'show',commit+':metadata/source_universes/approved_v1/manifest.json'])
assert hashlib.sha256(committed).hexdigest()==inputs[str(SCOPE/'metadata/source_universes/approved_v1/manifest.json')]
approval=load(SCOPE/'metadata/source_universes/approved_v1/owner_authorization.json')
assert approval['status']=='APPROVED' and approval['manifest_sha256']=='2198f9bad9c864bf339eff515992526e22efc4230160614a8f86daf3143f463c'
assert subprocess.check_output(['git','-C',str(SCOPE),'show',commit+':metadata/source_universes/approved_v1/owner_authorization.json'])==(SCOPE/'metadata/source_universes/approved_v1/owner_authorization.json').read_bytes()
f=load(ROOT/'metadata/freezes/C300_v1/freeze.json')
authorization=load(ROOT/'metadata/freezes/C300_v1/authorization.json')
assert inputs[str(ROOT/'metadata/freezes/C300_v1/authorization.json')]==f['files']['authorization.json']
assert authorization['admit_and_freeze'] is True

cids={r['source_instance_id'] for r in table(ROOT/'metadata/cohorts/C300.csv')}
manifest=table(ROOT/'metadata/corpus_manifest_v3.csv')
for name,key in [('metadata/cohorts/C300.csv','C300.csv'),('metadata/corpus_manifest_v3.csv','corpus_manifest_v3.csv')]: assert inputs[str(ROOT/name)]==f['files'][key]
c=[r for r in manifest if r['source_instance_id'] in cids]; assert len(c)==300
packet=load(LAB/'runs/c300/frozen-v1/review.json'); assert inputs[str(LAB/'runs/c300/frozen-v1/review.json')]==f['files']['review.json']
pm=packet['members']; assert {r['source_instance_id'] for r in pm}==cids
uid={m['identity'] for m in u['members']}; uh={m['raw_sha256'] for m in u['members']}
cidentity={m.get('delivery_id',m.get('candidate_id')) for m in pm}|{m['candidate_id'] for m in pm}
ch={m['raw_sha256'] for m in c}
checks=[]
for r in rows:
 checks.append(dict(source_instance_id=r['source_instance_id'],universe_identity_absent=r['candidate'] not in uid,universe_hash_absent=r['expected_sha256'] not in uh,c300_id_absent=r['source_instance_id'] not in cids,c300_identity_absent=r['candidate'] not in cidentity,c300_hash_absent=r['expected_sha256'] not in ch))
assert all(all(v for k,v in r.items() if k!='source_instance_id') for r in checks)
holdouts=[m for m in u['members'] if m['holdout']]; assert len(holdouts)==41
holdout_checks=[dict(identity=m['identity'],raw_sha256=m['raw_sha256'],c300_identity_absent=m['identity'] not in cidentity,c300_hash_absent=m['raw_sha256'] not in ch) for m in holdouts]
assert all(m['c300_identity_absent'] and m['c300_hash_absent'] for m in holdout_checks)
deps=[]
for day,increment,cumulative,version in [('day3','n450','C750',4),('day4','n750','C1500',5),('day5','n500','C2000',6)]:
 base=Path('/Users/lightnino/Projects/edp-lab-'+day)
 cohort={r['source_instance_id'] for r in table(base/f'metadata/cohorts/{cumulative}.csv')}
 cm=table(base/f'metadata/corpus_manifest_v{version}.csv'); byid={r['source_instance_id']:r for r in cm}
 included=[r for r in rows if r['source_instance_id'] in cohort]
 assert all(byid[r['source_instance_id']]['raw_sha256']==r['expected_sha256'] for r in included)
 completion=load(base/f'runs/{increment}/structural-v1/completion.json')
 review=load(base/f'runs/{increment}/frozen-v1/review.json')
 for name,digest in completion['membership_files'].items():
  p=base/name
  assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
  inputs[str(p)]=digest

 deps.append(dict(cohort=cumulative,retained_800_members=len(included),status='HISTORICAL_UNACCEPTED',structural_completion=str(base/f'runs/{increment}/structural-v1/completion.json'),historical_processing_jobs=completion['databricks_processing_jobs'],historical_clean_queryable=completion.get('CLEAN_QUERYABLE','NOT_ESTABLISHED_BY_THIS_SUMMARY'),historical_m1=completion.get('final_M1_fit',completion.get('final_B1_Model_Fit'))))
# Bounded known accepted-C300 processing dependencies; historical local evidence only.
b=LAB/'runs/c300-m1/main_recovery_20261021_v4'
contract=load(b/'contract.json')
assert contract['code_sha256']['metadata/cohorts/C300.csv']==f['files']['C300.csv']
assert contract['code_sha256']['metadata/corpus_manifest_v3.csv']==f['files']['corpus_manifest_v3.csv']
physical=load(b/'collected-full/physical.json')
assert set(physical)==cids
assert all(physical[r['source_instance_id']]['raw_sha256']==r['raw_sha256'] for r in c)
retained_ids={r['source_instance_id'] for r in rows}
assert not retained_ids.intersection(physical)
assert not {r['expected_sha256'] for r in rows}.intersection(m['raw_sha256'] for m in physical.values())
completion=load(b/'recovery-main-completion.json')
publication=load(b/'publication.json')
queryable=load(b/'collected-full/queryable.json')
jobs={phase:load(b/f'submitted-{phase}.json')['run_id'] for phase in ['stage','clean','gate','publish','query','finish']}
save('known_c300_consumers.json',dict(scope='Historical local retained evidence only; not live catalog certification',physical_count=len(physical),retained_800_intersection=0,contract=str(b/'contract.json'),physical_evidence=str(b/'collected-full/physical.json'),completion_status=completion['status'],freeze_status=completion['freeze_status'],tables=publication['versions'],queryable_views=list(queryable['views']),jobs=jobs,current_live_status='UNVERIFIED'))
save('exclusions.json',dict(verified_at=datetime.now(timezone.utc).isoformat(),approval_commit=commit,universe_count=len(u['members']),c300_count=len(cids),objects=checks,holdouts=holdout_checks))
save('dependencies.json',deps)
save('input_digests.json',inputs)
print(json.dumps(dict(excluded_universe=len(checks),excluded_c300=len(checks),holdouts_excluded=len(holdouts),historical_memberships={r['cohort']:r['retained_800_members'] for r in deps})))
