from pathlib import Path

FILE = Path(__file__).absolute()
HERE = FILE.parent
TEST_NOTES = HERE / 'data/test_notes'


def test_notecard_cache():
    from remy.notecard_cache import NotecardCache

    cache = NotecardCache(TEST_NOTES)

