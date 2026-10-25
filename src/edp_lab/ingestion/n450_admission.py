"""Guarded metadata-only N450 admission and C750 freeze; no RAW copying or parsing.

This module installs no authority. Publication requires the independent host-pinned
owner record, exact reviewed registration mapping and exact output file digests.
"""
import argparse
import csv
import io
import json
from datetime import datetime
from pathlib import Path

from edp_lab.ingestion import n450_authorization as auth
from edp_lab.ingestion.c300_admission import csv_bytes, encoded
from edp_lab.ingestion.gold_set import HEADERS
from edp_lab.ingestion.source_identity import ID_RE
from edp_lab.ingestion.universe import UniverseGate, sha

ADMISSION = Path("metadata/admissions/N450_v1")
FREEZE = Path("metadata/freezes/C750_v1")


def _read_rows(raw):
    reader = csv.DictReader(io.StringIO(raw.decode()))
    auth._require(reader.fieldnames == list(HEADERS), "MANIFEST_SCHEMA_MISMATCH")
    return list(reader)


def _publication(root, output, expected, files, scope):
    """Validate destination and entire bundle before first filesystem mutation.

    Exclusive directory creation forbids replacement. A completion marker is last;
    an interrupted directory is incomplete and is never accepted or overwritten.
    """
    root = Path(root).resolve()
    output = Path(output).absolute()
    target = root / expected
    auth._require(output == target and output.resolve() == target,
                  "PUBLICATION_DESTINATION_MISMATCH")
    auth._require(scope["destination"] == str(expected), "PUBLICATION_DESTINATION_MISMATCH")
    auth._require(not output.exists(), "PUBLICATION_ALREADY_EXISTS")
    hashes = {name: sha(raw) for name, raw in files.items()}
    auth._require(scope["files_sha256"] == hashes, "PUBLICATION_BYTES_NOT_APPROVED")
    # Every existing ancestor must be a directory, without symlinks. No creation
    # occurs on a denied request, including missing authority or changed inputs.
    auth._require(all(not p.is_symlink() and (not p.exists() or p.is_dir())
                  for p in [output.parent, *output.parent.parents]), "UNSAFE_PUBLICATION_PARENT")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    for name, raw in files.items():
        with (output / name).open("xb") as handle:
            handle.write(raw)
    return {"status": "PUBLISHED", "path": str(output), "files_sha256": hashes}


def admission_files(root, grant):
    """Pure metadata planning; final bytes must be reviewed and bound by the owner."""
    root = Path(root)
    original = (root / "metadata/corpus_manifest_v3.csv").read_bytes()
    rows = _read_rows(original)
    roster = json.loads((root / auth.PACKET / "roster.json").read_bytes())
    registrations = grant["registrations"]
    auth._require(len(registrations) == len(roster) == 450, "REGISTRATION_COUNT_MISMATCH")
    auth._require([r["source_identity"] for r in registrations] ==
                  [r["source_identity"] for r in roster], "REGISTRATION_SCOPE_MISMATCH")
    ids = [r["source_instance_id"] for r in registrations]
    auth._require(len(set(ids)) == 450 and all(ID_RE.fullmatch(i) for i in ids),
                  "INVALID_REGISTRATION_IDS")
    auth._require(not set(ids) & {r["source_instance_id"] for r in rows}, "REGISTRATION_ID_COLLISION")
    stamp = grant["admitted_at_utc"]
    auth._require(stamp.endswith("Z") and datetime.fromisoformat(stamp).utcoffset().total_seconds()
                  == 0, "INVALID_ADMISSION_TIME")
    bindings = []
    for member, registration in zip(roster, registrations, strict=True):
        row = dict(zip(HEADERS, (registration["source_instance_id"], member["family"], stamp,
                   "N450", member["raw_path"], member["raw_sha256"], "REAL", "", "", "FALSE",
                   "", "ADMITTED"), strict=True))
        rows.append(row)
        bindings.append({**registration, "raw_path": member["raw_path"],
                         "raw_sha256": member["raw_sha256"]})
    for field in ("source_instance_id", "raw_path", "raw_sha256"):
        auth._require(len({r[field] for r in rows}) == len(rows), "DUPLICATE_ADMISSION_BINDING")
    manifest = csv_bytes(HEADERS, rows)
    # Compare the parsed historical prefix and preserve its original bytes too.
    auth._require(_read_rows(manifest)[:len(rows)-450] == _read_rows(original),
                  "HISTORICAL_MANIFEST_CHANGED")
    files = {"corpus_manifest_v3.original.csv": original, "corpus_manifest_v4.csv": manifest,
             "N450.csv": csv_bytes(("source_instance_id",),
                                   [{"source_instance_id": i} for i in ids]),
             "bindings.json": encoded(bindings)}
    files["admission.json"] = encoded({"schema": "N450_ADMISSION_V1", "status": "ADMITTED",
        "universe": grant["universe"], "packet_sha256": auth.PINS,
        "files_sha256": {name: sha(raw) for name, raw in files.items()}})
    return files


def admit(root, bindings, output):
    """Actual publication entrypoint: authority/integrity precede all writes."""
    root = Path(root)
    approval = auth.authorize(root, "admission", bindings, cohort="N450")
    grant = approval["grant"]
    files = admission_files(root, grant)
    auth._require(sha((root / auth.OWNER_GRANT_PATH).read_bytes()) == approval["owner_grant_sha256"],
                  "OWNER_GRANT_CHANGED")
    return _publication(root, output, ADMISSION, files, grant["scopes"]["admission"])


def freeze_files(root, grant, admitted):
    """Build exact C750 union from unchanged C300 and reviewed admission bytes."""
    root = Path(root)
    historical = list(csv.DictReader((root / "metadata/cohorts/C300.csv").open()))
    increment = list(csv.DictReader(io.StringIO(admitted["N450.csv"].decode())))
    roster = historical + increment
    auth._require(len(historical) == 300 and len(increment) == 450 and
                  len({r["source_instance_id"] for r in roster}) == 750, "C750_ROSTER_MISMATCH")
    side = json.loads(UniverseGate.load_historical(root).bindings)
    historical_bindings = [{"source_identity": b["delivery_identity"],
                            "source_instance_id": b["identity"], "raw_path": b["raw_path"],
                            "raw_sha256": b["raw_sha256"]} for b in side["bindings"]
                           if b["identity"] in side["cohorts"]["C300"]["identities"]]
    bindings = historical_bindings + json.loads(admitted["bindings.json"])
    union = json.loads((root / auth.PACKET / "c750-proposed.json").read_bytes())
    auth._require({r["source_identity"]: r["raw_sha256"] for r in bindings} ==
                  {r["source_identity"]: r["raw_sha256"] for r in union}, "C750_UNION_MISMATCH")
    files = {**admitted, "C300.original.csv": (root / "metadata/cohorts/C300.csv").read_bytes(),
             "C750.csv": csv_bytes(("source_instance_id",), roster),
             "C750.bindings.json": encoded(bindings)}
    files["freeze.json"] = encoded({"schema": "C750_COHORT_FREEZE_V1", "status": "FROZEN",
        "universe": grant["universe"], "packet_sha256": auth.PINS,
        "files_sha256": {name: sha(raw) for name, raw in files.items()},
        "processing_authorization": "NOT_GRANTED", "output_freeze": "NOT_O_C750_M1"})
    return files


def freeze(root, bindings, output):
    """Require a complete exact admission before publishing a separate cohort freeze."""
    root = Path(root)
    approval = auth.authorize(root, "freeze", bindings, cohort="C750")
    grant = approval["grant"]
    expected = admission_files(root, grant)
    auth._require(sha((root / auth.OWNER_GRANT_PATH).read_bytes()) == approval["owner_grant_sha256"],
                  "OWNER_GRANT_CHANGED")
    # A marker alone cannot establish admission. Recompute every expected byte.
    directory = root / ADMISSION
    auth._require(not directory.is_symlink() and directory.resolve() == directory.absolute(),
                  "UNSAFE_ADMISSION_REFERENCE")
    auth._require({p.name for p in directory.iterdir()} == set(expected), "INCOMPLETE_ADMISSION")
    for name, raw in expected.items():
        path = directory / name
        auth._require(not path.is_symlink() and path.read_bytes() == raw, "ADMISSION_BYTES_CHANGED")
    auth._require(grant["scopes"]["admission"]["files_sha256"] ==
                  {name: sha(raw) for name, raw in expected.items()}, "ADMISSION_NOT_APPROVED")
    return _publication(root, output, FREEZE, freeze_files(root, grant, expected),
                        grant["scopes"]["freeze"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("admit", "freeze"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        bindings = json.loads(args.bindings.read_bytes())
        result = (admit if args.action == "admit" else freeze)(args.root, bindings, args.output)
        print(json.dumps(result, sort_keys=True))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"FAIL {exc}\n")


if __name__ == "__main__":
    main()
