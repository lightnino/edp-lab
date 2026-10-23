"""Make repository-local Day 6 scripts importable under CI's pytest entry point."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
