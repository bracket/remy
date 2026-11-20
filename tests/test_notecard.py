from pathlib import Path

FILE = Path(__file__).absolute()
HERE = FILE.parent
DATA = HERE / 'data'

def test_from_file():
    from remy import notecard

    print()

    for card in notecard.from_file(DATA / 'test_notes/notes_01'):
        print(card)
        print(card.source_url)
        print(card.labels)
        print(card.content)


def test_from_path():
    from remy import notecard

    print()

    for card in notecard.from_path(DATA / 'test_notes'):
        print(card)
        print(card.source_url)
        print(card.content)


def test_from_file_with_many_labels(tmp_path):
    from remy.notecard import from_file

    path = tmp_path / "cards.ntc"
    path.write_text("NOTECARD first\none\nNOTECARD second alias third fourth\ntwo\n")
    cards = list(from_file(path))
    assert [card.labels for card in cards] == [["first"], ["second", "alias", "third", "fourth"]]
    assert [card.content for card in cards] == ["one\n", "two\n"]
