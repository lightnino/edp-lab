"""Publish a reviewed cohort using the existing independently installed owner pin."""
import argparse
import json
from pathlib import Path

from edp_lab.ingestion import cohort_publication as publication
from edp_lab.ingestion import n450_authorization as authority
from edp_lab.ingestion.universe import sha

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('action', choices=('admission', 'freeze'))
    args = parser.parse_args()
    grant_raw = (ROOT / authority.OWNER_GRANT_PATH).read_bytes()
    # No proposal digest or command-line argument can install authority.
    grant = publication.authorize(
        args.plan.read_bytes(), grant_raw, authority.OWNER_GRANT_SHA256)
    for relative, digest in grant['execution_files_sha256'].items():
        path = ROOT / relative
        publication.require(path.resolve().is_relative_to(ROOT), 'UNSAFE_EVIDENCE_PATH')
        publication.require(sha(path.read_bytes()) == digest, 'EXECUTION_EVIDENCE_CHANGED')
    print(json.dumps(publication.publish(ROOT, args.plan.read_bytes(), grant_raw,
                                        authority.OWNER_GRANT_SHA256, args.action), sort_keys=True))


if __name__ == '__main__':
    main()
