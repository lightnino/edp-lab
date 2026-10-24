"""Prepare, but do not admit, exact C1500 + preserved N500 membership."""

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/day5"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def main() -> None:
    old_path = ROOT / "metadata/freezes/C1500_v1/C1500.bindings.json"
    proposal_path = RUN / "p1_p3_cohort_proposal_v1.json"
    p34_path = RUN / "p3_p4_contract_evidence_v1.json"
    old = json.loads(old_path.read_bytes())
    proposal = json.loads(proposal_path.read_bytes())
    p34 = json.loads(p34_path.read_bytes())
    selected = proposal["selected"]
    if (len(old) != 1500 or len(selected) != 500
            or p34["selected_count"] != 500
            or p34["preserved_evidence_sha256"]["p1_p3_cohort_proposal_v1.json"]
            != sha(proposal_path)
            or p34["prior_bindings_sha256"] != sha(old_path)):
        raise ValueError("PRESERVED_COHORT_EVIDENCE_CHANGED")
    prior_ids = {row["source_identity"] for row in old}
    prior_names = {row["source_instance_id"] for row in old}
    first = max(int(value[3:]) for value in prior_names) + 1
    names = [f"SRC{value:06d}" for value in range(first, first + 500)]
    if len(prior_ids) != 1500 or prior_names & set(names):
        raise ValueError("PRIOR_MEMBERSHIP_OR_ID_COLLISION")
    suffix = p34["selected_roster_sha256"][:12]
    prefix = f"dbfs:/Volumes/workspace/edp_lab/raw/day5-n500-{suffix}"
    new = []
    for name, source in zip(names, selected, strict=True):
        if source["identity"] in prior_ids or source["parser_validation"] != "PASS":
            raise ValueError("SELECTED_SOURCE_NOT_ELIGIBLE")
        raw = Path(source["raw_path"])
        new.append({"source_instance_id": name, "source_identity": source["identity"],
                    "source_family": "SEC_EDGAR_DAILY_MASTER",
                    "raw_path": str(raw), "raw_sha256": source["raw_sha256"],
                    "raw_bytes": source["bytes"], "data_records": source["data_records"],
                    "parser_profile_id": "SEC_EDGAR_DAILY_MASTER_C300_PARSER_V1",
                    "remote_raw_path": f"{prefix}/{source['identity']}/{raw.name}"})
    if len({row["source_identity"] for row in new}) != 500:
        raise ValueError("DUPLICATE_NEW_SOURCE")
    combined = old + [{k: row[k] for k in ("source_instance_id", "source_identity",
                                             "raw_path", "raw_sha256")} for row in new]
    output = RUN / "p6_candidate_v1"
    save_new(output / "N500.bindings.json",
             (json.dumps(new, sort_keys=True, indent=2) + "\n").encode())
    save_new(output / "C2000.bindings.json",
             (json.dumps(combined, sort_keys=True, indent=2) + "\n").encode())
    for label, rows in (("N500", new), ("C2000", combined)):
        path = output / f"{label}.csv"
        with path.open("x", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["source_instance_id"])
            writer.writerows([[row["source_instance_id"]] for row in rows])
    evidence = {"schema": "DAY5_P6_CANDIDATE_V1",
                "status": "PREPARED_NOT_ADMITTED_REMOTE_READBACK_PENDING",
                "prior_count": 1500, "new_count": 500, "combined_count": 2000,
                "remote_raw_prefix": prefix,
                "selected_evidence_sha256": sha(proposal_path),
                "p3_p4_evidence_sha256": sha(p34_path),
                "old_bindings_sha256": sha(old_path),
                "outputs_sha256": {path.name: sha(path) for path in output.iterdir()}}
    save_new(output / "candidate.json", (json.dumps(evidence, sort_keys=True,
                                                     indent=2) + "\n").encode())
    print(json.dumps({"status": evidence["status"], "prefix": prefix,
                      "new_count": 500, "combined_count": 2000}, sort_keys=True))


if __name__ == "__main__":
    main()
