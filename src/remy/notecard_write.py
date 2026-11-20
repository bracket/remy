"""Label-keyed creation, replacement, and deletion of notecards."""

from datetime import datetime, timezone
from enum import Enum
from io import StringIO
import os
from pathlib import Path
import tempfile

from .exceptions import RemyError
from .grammar import notecard_grammar
from .notecard import Notecard
from .util import generate_unique_label


class WriteResult(Enum):
    CREATED = "created"
    REPLACED = "replaced"
    DELETED = "deleted"
    NOOP = "noop"


class InvalidWriteError(RemyError):
    pass


class CardNotFoundError(RemyError):
    pass


class LabelConflictError(RemyError):
    pass


def _write_new_card(root, labels, text):
    while True:
        now = datetime.now(timezone.utc)
        directory = Path(root) / now.strftime("%Y/%m")
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (now.strftime("%d_%H%M%S%f") + ".ntc")
        try:
            fd = path.open("x", encoding="utf-8", newline="")
        except FileExistsError:
            continue
        try:
            with fd:
                fd.write("NOTECARD " + " ".join(labels) + "\n" + text)
            return path
        except Exception:
            path.unlink(missing_ok=True)
            raise


def _cut_card(card):
    path = Path(card.source_url.path)
    lines = path.read_bytes().splitlines(keepends=True)
    header = notecard_grammar()["notecard_start_line"]
    start = None
    end = len(lines)
    for index, line in enumerate(lines):
        decoded = line.decode("utf-8")
        if decoded.endswith("\r") and not decoded.endswith("\r\n"):
            decoded = decoded[:-1] + "\n"
        match = header.match(decoded)
        if match:
            if start is not None:
                end = index
                break
            if match.group("labels").split() == card.labels:
                start = index
    if start is None:
        raise RemyError(f"Notecard header not found in source file: {path}")

    remaining = b"".join(lines[:start] + lines[end:])
    if not remaining.strip():
        path.unlink()
        return

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as fd:
            temp_path = Path(fd.name)
            fd.write(remaining)
        os.chmod(temp_path, path.stat().st_mode)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def replace_card(cache, source_label=None, target_labels=None, text=None):
    """Write a card and return (WriteResult, Notecard or None)."""
    if source_label is not None and not isinstance(source_label, str):
        raise InvalidWriteError("source_label must be a string or null")
    if text is not None and not isinstance(text, str):
        raise InvalidWriteError("text must be a string or null")
    if isinstance(target_labels, str):
        target_labels = [target_labels]
    elif target_labels is not None and not isinstance(target_labels, list):
        raise InvalidWriteError("target_labels must be a string, list, or null")

    if target_labels is None and source_label is None:
        target_labels = [generate_unique_label()]
    elif target_labels is None:
        if text is not None:
            raise InvalidWriteError("text must be null when deleting a notecard")
        card = cache.find_card_by_label(source_label)
        if card is None:
            return WriteResult.NOOP, None
        _cut_card(card)
        return WriteResult.DELETED, None

    grammar = notecard_grammar()
    if not target_labels:
        raise InvalidWriteError("target_labels must not be empty")
    if any(not isinstance(label, str) or not grammar["label"].fullmatch(label) for label in target_labels):
        raise InvalidWriteError("Invalid target label")
    if len(set(target_labels)) != len(target_labels):
        raise InvalidWriteError("target_labels must not contain duplicates")
    text = text if text is not None else ""
    if any(grammar["notecard_start_line"].match(line) for line in StringIO(text, newline=None)):
        raise InvalidWriteError("text must not contain a notecard header")

    card = cache.find_card_by_label(source_label) if source_label is not None else None
    if source_label is not None and card is None:
        raise CardNotFoundError(f"Notecard with label '{source_label}' not found")
    for label in target_labels:
        existing = cache.find_card_by_label(label)
        if existing is not None and existing is not card:
            raise LabelConflictError(f"Label '{label}' belongs to another notecard")

    path = _write_new_card(cache.url.path, target_labels, text)
    if card is not None:
        try:
            _cut_card(card)
        except Exception:
            path.unlink(missing_ok=True)
            raise
    new_card = Notecard(target_labels, text)
    return (WriteResult.REPLACED if card is not None else WriteResult.CREATED), new_card
