"""Host-owned experiment authority. Requests and RAW retention confer no authority.

The deployment pin names the exact owner-approved Universe v1 artifact.
Changing this pin is a human-reviewed code/configuration deployment, never a tool argument.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

AUTHORITY_PATH = Path("metadata/source_universes/approved_v1/manifest.json")
# Single active Universe entrypoint for future cohort runs. The legacy pinned
# v1 path above remains read-only for previously accepted historical executions.
ACTIVE_AUTHORITY_PATH = Path("metadata/source_universes/approved/manifest.json")
APPROVED_AUTHORITY_SHA256 = "2198f9bad9c864bf339eff515992526e22efc4230160614a8f86daf3143f463c"
APPROVAL_SHA256 = "3307ff5c234e20b48a7a2ced6de7c54d504eb475de8ae90d4509cfd49002823d"
BINDINGS_PATH = Path("metadata/source_universes/historical_cohort_bindings_v1.json")
BINDINGS_SHA256 = "8ffd02e0322241c5815a629f51a6d9c1590c2baa83231808ac796a450c6f2904"


class ScopeDenied(ValueError):
    def __init__(self, reason, **refs):
        self.outcome = {
            "status": "OUT_OF_SCOPE",
            "code": "AUTHORIZATION_REQUIRED",
            "decision": "DENY",
            "reason": reason,
            "approval_required": True,
            "route": "Human Review",
            "evidence_refs": refs,
        }
        super().__init__(json.dumps(self.outcome, sort_keys=True))

    def __str__(self):
        return json.dumps(self.outcome, sort_keys=True)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class UniverseGate:
    """Immutable bytes pinned by trusted host, not by Agent-supplied approvals."""

    authority: bytes
    fingerprint: str
    bindings: bytes | None = None

    @classmethod
    def load_active(cls, root, *, manifest_sha256: str, approval_sha256: str):
        """Load exactly one active Universe, pinned by trusted deployment.

        Pins must be supplied by the protected actor; never from an Agent's
        untrusted run request. The active path contains no _v1/_v2 suffix.
        """
        import re

        if not all(isinstance(pin, str) and re.fullmatch(r"[0-9a-f]{64}", pin)
                   for pin in (manifest_sha256, approval_sha256)):
            raise ScopeDenied("INVALID_ACTIVE_UNIVERSE_PIN")
        path = root / ACTIVE_AUTHORITY_PATH
        try:
            raw = path.read_bytes()
        except OSError:
            raise ScopeDenied("MISSING_ACTIVE_UNIVERSE") from None
        if sha(raw) != manifest_sha256:
            raise ScopeDenied("AUTHORITY_PIN_MISMATCH")
        try:
            document = json.loads(raw)
            approval_rel = Path(document["approval_reference"])
            if approval_rel.is_absolute() or ".." in approval_rel.parts:
                raise ValueError("Unsafe approval path")
            approval_raw = (root / approval_rel).read_bytes()
            approval = json.loads(approval_raw)
            if (sha(approval_raw) != approval_sha256
                    or approval.get("status") != "APPROVED"
                    or approval.get("manifest_sha256") != manifest_sha256):
                raise ValueError("Invalid owner approval")
        except (OSError, ValueError, KeyError, TypeError):
            raise ScopeDenied("INVALID_OWNER_OR_COHORT_EVIDENCE") from None
        gate = cls(raw, manifest_sha256)
        gate.document()  # Validate all members and collision/holdout shape.
        return gate

    @classmethod
    def load(cls, root):
        try:
            raw = (root / AUTHORITY_PATH).read_bytes()
        except OSError:
            raise ScopeDenied("MISSING_HOST_AUTHORITY", reference=str(AUTHORITY_PATH)) from None
        if sha(raw) != APPROVED_AUTHORITY_SHA256:
            raise ScopeDenied("AUTHORITY_PIN_MISMATCH")
        if (
            APPROVED_AUTHORITY_SHA256
            == "2198f9bad9c864bf339eff515992526e22efc4230160614a8f86daf3143f463c"
        ):
            try:
                approval_raw = (root / json.loads(raw)["approval_reference"]).read_bytes()
                approval = json.loads(approval_raw)
                if not sha(approval_raw) == APPROVAL_SHA256:
                    raise ValueError("Invalid authority evidence")
                if not approval["status"] == "APPROVED":
                    raise ValueError("Invalid authority evidence")
                if not approval["manifest_sha256"] == sha(raw):
                    raise ValueError("Invalid authority evidence")
                side_raw = (root / BINDINGS_PATH).read_bytes()
                if not sha(side_raw) == BINDINGS_SHA256:
                    raise ValueError("Invalid authority evidence")
                side = json.loads(side_raw)
                if not side["universe_manifest_sha256"] == sha(raw):
                    raise ValueError("Invalid authority evidence")
                if not side["universe_version"] == "1":
                    raise ValueError("Invalid authority evidence")
                for path, digest in side["evidence"].items():
                    if not sha((root / path).read_bytes()) == digest:
                        raise ValueError("Invalid authority evidence")
            except (OSError, ValueError, KeyError, AssertionError):
                raise ScopeDenied("INVALID_OWNER_OR_COHORT_EVIDENCE") from None
            return cls(raw, APPROVED_AUTHORITY_SHA256, side_raw)
        return cls(raw, APPROVED_AUTHORITY_SHA256)

    def document(self):
        if not self.fingerprint or sha(self.authority) != self.fingerprint:
            raise ScopeDenied("AUTHORITY_PIN_MISMATCH")
        try:
            doc = json.loads(self.authority)
            if not doc["schema"] == "SOURCE_UNIVERSE_AUTHORITY_V1":
                raise ValueError("Invalid authority evidence")
            if not (doc["universe_version"] and doc["approval_reference"]):
                raise ValueError("Invalid authority evidence")
            if not (doc["inventory_reference"] and doc["inventory_sha256"]):
                raise ValueError("Invalid authority evidence")
            members = doc["members"]
            if not len(members) == doc["member_count"]:
                raise ValueError("Invalid authority evidence")
            if not len({m["identity"] for m in members}) == len(members):
                raise ValueError("Invalid authority evidence")
            if not all(
                type(m["holdout"]) is bool
                and m["identity"]
                and m["raw_path"]
                and (len(m["raw_sha256"]) == 64)
                for m in members
            ):
                raise ValueError("Invalid authority evidence")
            identities = [
                identity
                for m in members
                for identity in [m["identity"], *[b["identity"] for b in m.get("bindings", [])]]
            ]
            if not len(identities) == len(set(identities)):
                raise ValueError("Invalid authority evidence")
            if self.bindings is not None:
                if not sha(self.bindings) == BINDINGS_SHA256:
                    raise ValueError("Invalid authority evidence")
                side = json.loads(self.bindings)
                if not side["universe_manifest_sha256"] == self.fingerprint:
                    raise ValueError("Invalid authority evidence")
                indexed = {m["identity"]: m for m in members}
                for binding in side["bindings"]:
                    member = indexed[binding["delivery_identity"]]
                    if not member["raw_sha256"] == binding["raw_sha256"]:
                        raise ValueError("Invalid authority evidence")
                    member.setdefault("bindings", []).append(binding)
                doc["cohorts"] = side["cohorts"]
            return doc
        except (ValueError, KeyError, TypeError, AssertionError):
            raise ScopeDenied("INVALID_AUTHORITY") from None

    def check(self, identity, raw_sha256, raw_path, *, cohort=None, version=None):
        doc = self.document()
        refs = {
            "universe_version": doc["universe_version"],
            "authority_sha256": self.fingerprint,
            "identity": identity,
            "raw_sha256": raw_sha256,
            "raw_path": raw_path,
            "cohort": cohort,
        }
        if version is not None and version != doc["universe_version"]:
            raise ScopeDenied("UNIVERSE_VERSION_MISMATCH", **refs)
        member = next(
            (
                m
                for m in doc["members"]
                if m["identity"] == identity
                or any((b["identity"] == identity for b in m.get("bindings", [])))
            ),
            None,
        )
        if member is None:
            raise ScopeDenied("NOT_IN_APPROVED_UNIVERSE", **refs)
        paths = ([member["raw_path"]] if member["identity"] == identity else []) + [
            b["raw_path"] for b in member.get("bindings", []) if b["identity"] == identity
        ]
        if member["raw_sha256"] != raw_sha256 or raw_path not in paths:
            raise ScopeDenied("IDENTITY_EVIDENCE_MISMATCH", **refs)
        if member["holdout"]:
            raise ScopeDenied("RESERVED_HOLDOUT", **refs)
        if cohort is not None:
            roster = doc.get("cohorts", {}).get(cohort)
            if not roster or not {
                identity,
                *[
                    b["identity"]
                    for b in member.get("bindings", [])
                    if member["identity"] == identity
                ],
            } & set(roster["identities"]):
                raise ScopeDenied("NOT_IN_PINNED_COHORT", **refs)
        return {**refs, "physical_identity": member["identity"]}

    def scope_reference(self):
        doc = self.document()
        return {
            "universe_id": doc.get("universe_id", "TEST_ONLY"),
            "universe_version": doc["universe_version"],
            "universe_manifest_sha256": self.fingerprint,
        }

    def feasibility(self, requested_count, cohort):
        doc = self.document()
        roster = doc.get("cohorts", {}).get(cohort, {}).get("identities", [])
        eligible = set()
        for member in doc["members"]:
            if not member["holdout"]:
                aliases = {member["identity"], *[b["identity"] for b in member.get("bindings", [])]}
                if aliases & set(roster):
                    eligible.add(member["identity"])
        if type(requested_count) is not int or requested_count < 0:
            raise ScopeDenied("INVALID_REQUESTED_COUNT")
        if requested_count > len(eligible):
            denial = ScopeDenied(
                "INSUFFICIENT_AUTHORIZED_SOURCES",
                requested_count=requested_count,
                eligible_authorized_count=len(eligible),
                cohort=cohort,
            )
            denial.outcome["code"] = "INSUFFICIENT_AUTHORIZED_SOURCES"
            raise denial
        return len(eligible)

    def validate_inputs(self, bindings, cohort):
        """Validate the complete explicit input set before any caller opens RAW."""
        seen = set()
        for binding in bindings:
            identity = binding["source_instance_id"]
            reference = self.check(identity, binding["raw_sha256"], binding["raw_path"], cohort=cohort)
            physical = reference["physical_identity"]
            if physical in seen:
                raise ScopeDenied("DUPLICATE_PHYSICAL_INPUT", identity=identity)
            seen.add(physical)
        return self.scope_reference()

    def verify_inventory(self, root):
        doc = self.document()
        try:
            raw = (root / doc["inventory_reference"]).read_bytes()
        except OSError:
            raise ScopeDenied("MISSING_INVENTORY_EVIDENCE") from None
        if sha(raw) != doc["inventory_sha256"]:
            raise ScopeDenied("INVENTORY_HASH_MISMATCH")


def enforce(root, identity, raw_sha256, raw_path, *, cohort=None):
    gate = UniverseGate.load(root)
    gate.verify_inventory(root)
    return gate.check(identity, raw_sha256, raw_path, cohort=cohort)


def processing(root, binding, cohort):
    """Host selects fixed run name; no directory discovery or request scope changes."""
    if cohort in {"N450", "C750"}:
        from edp_lab.ingestion.n450_authorization import authorize

        enforce(root, binding["source_instance_id"], binding["raw_sha256"], binding["raw_path"])
        return authorize(root, "processing", [binding], cohort=cohort)
    return enforce(
        root,
        binding["source_instance_id"],
        binding["raw_sha256"],
        binding["raw_path"],
        cohort=cohort,
    )
