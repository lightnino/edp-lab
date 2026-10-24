"""Derive Day 5 P3/P4 evidence from the preserved P1/P2/P3 files only.

No RAW file is opened, selected or rescanned. This is not a processing grant.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/day5"
EVIDENCE = (
    "p0_p1_candidate_evidence_v1.json",
    "p1_p2_source_evidence_v1.json",
    "p1_p3_cohort_proposal_v1.json",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    p1, p2, proposal = [json.loads((RUN / name).read_bytes()) for name in EVIDENCE]
    refs = {name: sha(RUN / name) for name in EVIDENCE}
    if (proposal["old_candidate_evidence_sha256"] != refs[EVIDENCE[1]]
            or any(x["selected_count"] != 500 for x in (p1, p2, proposal))):
        raise ValueError("PRESERVED_CHECKPOINT_CHANGED")
    universe_path = ROOT / "metadata/source_universes/approved_v1/manifest.json"
    if sha(universe_path) != proposal["universe_manifest_sha256"]:
        raise ValueError("UNIVERSE_CHANGED")
    universe = {m["identity"]: m for m in json.loads(universe_path.read_bytes())["members"]}
    old_path = ROOT / "metadata/freezes/C1500_v1/C1500.bindings.json"
    if sha(old_path) != proposal["c1500_bindings_sha256"]:
        raise ValueError("OLD_ROSTER_CHANGED")
    old_ids = {row["source_identity"] for row in json.loads(old_path.read_bytes())}
    parser_path = ROOT / "src/edp_lab/parsers/c300_v1.py"
    if sha(parser_path) != proposal["parser_code_sha256"]:
        raise ValueError("PARSER_CHANGED")
    selected = proposal["selected"]
    ids = [row["identity"] for row in selected]
    if len(ids) != len(set(ids)) or len(ids) != 500 or old_ids & set(ids):
        raise ValueError("SELECTED_ROSTER_INVALID")
    for row in selected:
        member = universe.get(row["identity"])
        if (member is None or member["holdout"] or member["raw_path"] != row["raw_path"]
                or member["raw_sha256"] != row["raw_sha256"]
                or row["parser_validation"] != "PASS"
                or row["header"] != ["CIK", "Company Name", "Form Type", "Date Filed",
                                     "File Name"]
                or row["parser_errors"]):
            raise ValueError("SELECTED_SOURCE_OUT_OF_SCOPE")
    held = proposal["held_parser_exception"]
    if any(row["identity"] in ids for row in held):
        raise ValueError("HELD_EXCEPTION_ADMITTED")
    model = ROOT / "src/edp_lab/materialization/c300_m1.py"
    packet = {
        "schema": "DAY5_P3_P4_FROM_PRESERVED_V1",
        "status": "P3_CORPUS_ONLY_P4_APPROVED_LEXICAL_CONTRACT_REUSED",
        "authority": "MECHANICAL_EVIDENCE_ONLY_NO_ADMISSION_OR_EXECUTION_GRANT",
        "preserved_evidence_sha256": refs,
        "universe_sha256": sha(universe_path),
        "prior_bindings_sha256": sha(old_path),
        "selected_count": len(ids),
        "selected_roster_sha256": hashlib.sha256((json.dumps(ids, separators=(",", ":"))
                                                    + "\n").encode()).hexdigest(),
        "selected_data_records_in_prior_evidence": sum(x["data_records"] for x in selected),
        "held_parser_exceptions": [{"identity": x["identity"],
                                    "raw_sha256": x["raw_sha256"]} for x in held],
        "p3_route": "CORPUS_ONLY",
        "p3_basis": "500 preserved full-byte lexical PASS records, same approved SEC master "
                    "header/parser family, approved Universe, no holdout or C1500 overlap; "
                    "the failed parser instance remains held",
        "p4_parser": {"version": "C300_PARSER_V1", "path": str(parser_path.relative_to(ROOT)),
                      "sha256": sha(parser_path)},
        "p4_model": {"version": "M1_LEXICAL_V1", "path": str(model.relative_to(ROOT)),
                     "sha256": sha(model)},
        "p4_rule": "C300_LITERAL_IDENTITY_V1",
        "old_m2_result": "metadata/freezes/O_C1500_M2_v1/databricks_result_freeze_v2.json",
        "historical_replay": "NONE_FOR_CORPUS_ONLY",
        "new_semantic_rule": "NONE",
        "remote_raw_readback": "NOT_YET_VERIFIED",
        "execution_contract": "PENDING_PINNED_N500_RUNTIME_AND_PROTECTED_0A",
    }
    target = RUN / "p3_p4_contract_evidence_v1.json"
    with target.open("x") as stream:
        json.dump(packet, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({"status": packet["status"], "selected": len(ids),
                      "held": len(held), "evidence_sha256": sha(target)}, sort_keys=True))


if __name__ == "__main__":
    main()
