from pathlib import Path
from remy.url import URL

def test_url():
    test = URL('http://www.google.com')

    assert test.scheme == 'http'
    assert test.netloc == 'www.google.com'
    assert test.path == Path('.')
    assert test.params == ''
    assert test.query == ''
    assert test.fragment == ''

    FILE = Path(__file__).absolute()
    test = URL(FILE)

    assert test.scheme == 'file'
    assert test.netloc == ''
    assert test.path == FILE
    assert test.params == ''
    assert test.query == ''
    assert test.fragment == ''
