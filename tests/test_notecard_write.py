from datetime import datetime, timezone
import os
import re
from unittest.mock import patch

import pytest

from remy.notecard import from_file
from remy.notecard_cache import NotecardCache
from remy.notecard_write import (
    CardNotFoundError, InvalidWriteError, LabelConflictError, WriteResult, replace_card,
)


def cache(path):
    return NotecardCache(path)


def test_create_generated_label_and_empty_text(tmp_path):
    result, card = replace_card(cache(tmp_path), None, None, None)
    assert result is WriteResult.CREATED
    assert re.fullmatch(r"[0-9a-f]{64}", card.labels[0])
    assert card.content == ""
    paths = list(tmp_path.rglob("*.ntc"))
    assert len(paths) == 1
    assert re.fullmatch(r"\d{4}/\d{2}/\d{2}_\d{12}\.ntc", str(paths[0].relative_to(tmp_path)))
    assert list(from_file(paths[0]))[0].labels == card.labels


@pytest.mark.parametrize("labels", ["one", ["one", "two", "three"]])
@pytest.mark.parametrize("text", [None, "", "body\n"])
def test_create_explicit_labels(tmp_path, labels, text):
    result, card = replace_card(cache(tmp_path), None, labels, text)
    assert result is WriteResult.CREATED
    assert card.labels == ([labels] if isinstance(labels, str) else labels)
    assert card.content == (text or "")
    assert cache(tmp_path).find_card_by_label("one").content == (text or "")


@pytest.mark.parametrize("text", ["body\n:STATUS: DONE", "body\n:STATUS: DONE\n"])
def test_trailing_field_without_newline_is_parsed(tmp_path, text):
    from remy.ast import Field
    from remy.ast.parse import parse_content

    replace_card(cache(tmp_path), None, "one", text)
    path = next(tmp_path.rglob("*.ntc"))
    assert path.read_text() == "NOTECARD one\nbody\n:STATUS: DONE\n"
    content = cache(tmp_path).find_card_by_label("one").content
    fields = [n for n in parse_content(content) if isinstance(n, Field)]
    assert [(f.label, f.value) for f in fields] == [("STATUS", "DONE")]


def test_replace_by_alias_preserves_other_card_bytes(tmp_path):
    path = tmp_path / "mixed.ntc"
    before = b"prefix\r\nNOTECARD first old alias\r\nold body\r\n"
    after = b"NOTECARD other third\r\nother body\r\n"
    path.write_bytes(before + after)
    old_cache = cache(tmp_path)
    assert old_cache.find_card_by_label("old") is not None
    path.write_bytes(b"added line\r\n" + before + after)

    result, card = replace_card(old_cache, "old", ["first", "new", "extra"], "new body")
    assert result is WriteResult.REPLACED
    assert card.labels == ["first", "new", "extra"]
    assert path.read_bytes() == b"added line\r\nprefix\r\n" + after
    new_cache = cache(tmp_path)
    assert new_cache.find_card_by_label("old") is None
    assert new_cache.find_card_by_label("new").content == "new body\n"
    assert new_cache.find_card_by_label("third").content == "other body\n"


def test_delete_and_noop(tmp_path):
    path = tmp_path / "only.ntc"
    path.write_bytes(b" \r\nNOTECARD one alias\r\nbody\r\n")
    assert replace_card(cache(tmp_path), "alias", None, None) == (WriteResult.DELETED, None)
    assert not path.exists()
    assert replace_card(cache(tmp_path), "missing", None, None) == (WriteResult.NOOP, None)


def test_delete_middle_card_preserves_both_neighbors(tmp_path):
    path = tmp_path / "cards.ntc"
    first = b"NOTECARD first\r\nfirst body\r\n"
    middle = b"NOTECARD middle\r\nmiddle body\r\n"
    last = b"NOTECARD last\r\nlast body"
    path.write_bytes(first + middle + last)
    assert replace_card(cache(tmp_path), "middle", None, None) == (WriteResult.DELETED, None)
    assert path.read_bytes() == first + last


def test_cut_temp_file_is_hidden_from_cache(tmp_path):
    path = tmp_path / "cards.ntc"
    path.write_text("NOTECARD one\nfirst\nNOTECARD two\nsecond\n")
    real_replace = os.replace

    def check_and_replace(source, destination):
        assert source.name.startswith(".")
        assert set(cache(tmp_path).cards_by_label) == {"one", "two"}
        real_replace(source, destination)

    with patch("remy.notecard_write.os.replace", side_effect=check_and_replace):
        replace_card(cache(tmp_path), "one", None, None)
    assert set(cache(tmp_path).cards_by_label) == {"two"}


@pytest.mark.parametrize("source,labels,text", [
    ("missing", None, "body"), (None, [], None), (None, [""], ""),
    (None, ["bad label"], ""), (None, ["valid", "valid"], ""),
    (None, ["valid", 1], ""), (None, ["valid"], "body\nNOTECARD another\n"),
    (None, ["valid"], "NOTECARD another\r"),
])
def test_invalid_input(tmp_path, source, labels, text):
    with pytest.raises(InvalidWriteError):
        replace_card(cache(tmp_path), source, labels, text)
    assert list(tmp_path.iterdir()) == []


def test_not_found_and_conflict(tmp_path):
    (tmp_path / "cards.ntc").write_text("NOTECARD first alias\none\nNOTECARD second\ntwo\n")
    with pytest.raises(CardNotFoundError):
        replace_card(cache(tmp_path), "missing", ["new"], "text")
    with pytest.raises(LabelConflictError):
        replace_card(cache(tmp_path), "alias", ["first", "second"], "text")
    with pytest.raises(LabelConflictError):
        replace_card(cache(tmp_path), None, ["second"], "text")
    assert len(list(tmp_path.rglob("*.ntc"))) == 1


def test_collision_retries_without_overwriting(tmp_path):
    first = datetime(2026, 1, 2, 3, 4, 5, 6, tzinfo=timezone.utc)
    second = datetime(2026, 1, 2, 3, 4, 5, 7, tzinfo=timezone.utc)
    directory = tmp_path / "2026" / "01"
    directory.mkdir(parents=True)
    existing = directory / "02_030405000006.ntc"
    existing.write_text("NOTECARD existing\nold")
    with patch("remy.notecard_write.datetime") as clock:
        clock.now.side_effect = [first, second]
        result, _ = replace_card(cache(tmp_path), None, ["new"], "body")
    assert result is WriteResult.CREATED
    assert existing.read_text() == "NOTECARD existing\nold"
    assert (directory / "02_030405000007.ntc").read_text() == "NOTECARD new\nbody\n"


def test_failed_cut_removes_new_file(tmp_path):
    path = tmp_path / "cards.ntc"
    path.write_text("NOTECARD one\nbody\n")
    old_cache = cache(tmp_path)
    old_cache.cards_by_label
    path.write_text("NOTECARD changed\nbody\n")
    with pytest.raises(Exception, match="header not found"):
        replace_card(old_cache, "one", ["one"], "new")
    assert path.read_text() == "NOTECARD changed\nbody\n"
    assert list(tmp_path.rglob("*.ntc")) == [path]
