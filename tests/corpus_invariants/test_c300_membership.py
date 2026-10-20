"""C300 is unavailable; admitted GOLD membership is tested in existing suites."""

import pytest


@pytest.mark.skip(reason="C300 not admitted; no frozen roster or reviewed parser registration")
def test_actual_c300_membership():
    """Unavailable cohort-specific check, never a claim of 300-source validation."""
