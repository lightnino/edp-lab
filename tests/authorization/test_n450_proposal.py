"""One retained legitimate object cannot cross the actual authorization entrypoint."""
import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from edp_lab.ingestion.universe import ScopeDenied, processing


def test_retained_valid_hash_outside_source_denied_before_side_effect():
    root = Path(__file__).resolve().parents[2]
    evidence = root / 'proposals/n450-v1/qualification.json'
    if not evidence.exists():
        pytest.skip('Local proposal evidence unavailable')
    negative = json.loads(evidence.read_text())['negative_test']
    refs = negative['outcome']['evidence_refs']
    raw = Path(refs['raw_path'])
    if not raw.exists():
        pytest.skip('Retained original RAW unavailable')
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == refs['raw_sha256']
    side_effect = Mock()
    with pytest.raises(ScopeDenied) as caught:
        processing(root, {'source_instance_id': refs['identity'], 'raw_path': str(raw),
                              'raw_sha256': refs['raw_sha256']}, 'N450')
        side_effect()  # Represents admission/freeze/upload/profile/RAW consumer.
    assert caught.value.outcome['status'] == 'OUT_OF_SCOPE'
    assert caught.value.outcome['code'] == 'AUTHORIZATION_REQUIRED'
    assert caught.value.outcome['reason'] == 'NOT_IN_APPROVED_UNIVERSE'
    side_effect.assert_not_called()
