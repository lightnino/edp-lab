"""Print local V3 pins/authority gaps without making external calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from edp_lab.vault.v3_readiness import readiness


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--signed-semantic-envelope", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    print(json.dumps(readiness(root, args.signed_semantic_envelope),
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
