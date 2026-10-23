"""Negative controls for proposed Day 6 technical identity and lexical hashdiff."""

import pytest

from scripts.day6_vault_occurrence_probe import occurrence_key, payload_hashdiff


def test_occurrence_uses_physical_interval_not_run_or_content():
    first = {"run_id": "original", "source_id": "SRC000064", "member": "num.txt",
             "offset": 551534885, "length": 187}
    replay = {**first, "run_id": "replay"}
    key = occurrence_key(first["source_id"], first["member"], first["offset"], first["length"])
    assert key == occurrence_key(replay["source_id"], replay["member"],
                                 replay["offset"], replay["length"])
    assert key != occurrence_key("SRC000064", "num.txt", 551536714, 187)
    assert key != occurrence_key("SRC000054", "num.txt", 551534885, 187)
    assert key != occurrence_key("SRC000064", "tag.txt", 551534885, 187)


def test_lexical_hashdiff_preserves_empty_ordinal_and_spelling():
    names = ["value", "footnote"]
    base = payload_hashdiff(names, ["0.4700", ""])
    assert base == payload_hashdiff(names, ["0.4700", ""])
    assert base != payload_hashdiff(names, ["0.47", ""])
    assert base != payload_hashdiff(names, ["0.4700", "note"])
    assert base != payload_hashdiff(["footnote", "value"], ["", "0.4700"])
    with pytest.raises(ValueError, match="FIELD_WIDTH_MISMATCH"):
        payload_hashdiff(names, ["0.4700"])
