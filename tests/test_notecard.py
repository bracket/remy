from pathlib import Path

FILE = Path(__file__).absolute()
HERE = FILE.parent
DATA = HERE / 'data'

def test_from_file():
    from remy import notecard

    print()

    for card in notecard.from_file(DATA / 'test_notes/notes_01'):
        print(card)
        print(card.labels)
        print(card.content)


def test_from_path():
    from remy import notecard

    print()

    for card in notecard.from_path(DATA / 'test_notes'):
        print(card)
        print(card.source_url)
        print(card.content)
