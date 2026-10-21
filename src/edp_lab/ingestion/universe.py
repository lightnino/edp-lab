"""Host-owned experiment authority. Requests and RAW retention confer no authority.

The deployment pin is deliberately unset until reviewed evidence is installed.
Changing this pin is a human-reviewed code/configuration deployment, never a tool argument.
"""
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

AUTHORITY_PATH = Path('metadata/source_universe_authority.json')
APPROVED_AUTHORITY_SHA256 = None


class ScopeDenied(ValueError):
    def __init__(self, reason, **refs):
        self.outcome = {'status': 'OUT_OF_SCOPE', 'code': 'AUTHORIZATION_REQUIRED',
                            'decision': 'DENY', 'reason': reason, 'approval_required': True,
                            'route': 'Human Review', 'evidence_refs': refs}
        super().__init__(json.dumps(self.outcome, sort_keys=True))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class UniverseGate:
    """Immutable bytes pinned by trusted host, not by Agent-supplied approvals."""
    authority: bytes
    fingerprint: str

    @classmethod
    def load(cls, root):
        try:
            raw = (root / AUTHORITY_PATH).read_bytes()
        except OSError:
            raise ScopeDenied('MISSING_HOST_AUTHORITY', reference=str(AUTHORITY_PATH)) from None
        return cls(raw, APPROVED_AUTHORITY_SHA256)

    def document(self):
        if not self.fingerprint or sha(self.authority) != self.fingerprint:
            raise ScopeDenied('AUTHORITY_PIN_MISMATCH')
        try:
            doc = json.loads(self.authority)
            assert doc['schema'] == 'SOURCE_UNIVERSE_AUTHORITY_V1'
            assert doc['universe_version'] and doc['approval_reference']
            assert doc['inventory_reference'] and doc['inventory_sha256']
            members = doc['members']
            assert len(members) == doc['member_count']
            assert len({m['identity'] for m in members}) == len(members)
            assert all(type(m['holdout']) is bool and m['identity'] and m['raw_path']
                       and len(m['raw_sha256']) == 64 for m in members)
            identities = [identity for m in members
                          for identity in [m['identity'], *[b['identity']
                                           for b in m.get('bindings', [])]]]
            assert len(identities) == len(set(identities))
            return doc
        except (ValueError, KeyError, TypeError, AssertionError):
            raise ScopeDenied('INVALID_AUTHORITY') from None

    def check(self, identity, raw_sha256, raw_path, *, cohort=None, version=None):
        doc = self.document()
        refs = {'universe_version': doc['universe_version'], 'authority_sha256': self.fingerprint,
                    'identity': identity, 'raw_sha256': raw_sha256, 'raw_path': raw_path, 'cohort': cohort}
        if version is not None and version != doc['universe_version']:
            raise ScopeDenied('UNIVERSE_VERSION_MISMATCH', **refs)
        member = next((m for m in doc['members'] if m['identity'] == identity
                       or any(b['identity'] == identity for b in m.get('bindings', []))), None)
        if member is None:
            raise ScopeDenied('NOT_IN_APPROVED_UNIVERSE', **refs)
        paths = [member['raw_path']] if member['identity'] == identity else [
            b['raw_path'] for b in member.get('bindings', []) if b['identity'] == identity]
        if member['raw_sha256'] != raw_sha256 or raw_path not in paths:
            raise ScopeDenied('IDENTITY_EVIDENCE_MISMATCH', **refs)
        if member['holdout']:
            raise ScopeDenied('RESERVED_HOLDOUT', **refs)
        if cohort is not None:
            roster = doc.get('cohorts', {}).get(cohort)
            if not roster or identity not in roster['identities']:
                raise ScopeDenied('NOT_IN_PINNED_COHORT', **refs)
        return refs

    def verify_inventory(self, root):
        doc = self.document()
        try:
            raw = (root / doc['inventory_reference']).read_bytes()
        except OSError:
            raise ScopeDenied('MISSING_INVENTORY_EVIDENCE') from None
        if sha(raw) != doc['inventory_sha256']:
            raise ScopeDenied('INVENTORY_HASH_MISMATCH')


def enforce(root, identity, raw_sha256, raw_path, *, cohort=None):
    gate = UniverseGate.load(root)
    gate.verify_inventory(root)
    return gate.check(identity, raw_sha256, raw_path, cohort=cohort)


def processing(root, binding, cohort):
    """Host selects fixed run name; no directory discovery or request scope changes."""
    return enforce(root, binding['source_instance_id'], binding['raw_sha256'],
                   binding['raw_path'], cohort=cohort)
