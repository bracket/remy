from urllib.parse import urlparse, ParseResult
from pathlib import Path

class URL(ParseResult):
    def __new__(cls, url, *args, **kwargs):
        if isinstance(url, URL):
            return url

        parsed = None

        if isinstance(url, ParseResult):
            parsed = url
            scheme = parsed.scheme
            path = Path(parsed.path)
        elif isinstance(url, Path):
            scheme = 'file'
            path = url
        else:
            parsed = urlparse(url)
            scheme = parsed.scheme
            path = Path(parsed.path)

        return super(URL, cls).__new__(
            cls,
            scheme,
            parsed.netloc if parsed else '',
            path,
            parsed.params if parsed else '',
            parsed.query if parsed else '',
            parsed.fragment if parsed else ''
        )


    def geturl(self):
        path = str(self.path)

        if path == '.':
            path = ''

        return ParseResult(
            self.scheme,
            self.netloc,
            path,
            self.params,
            self.query,
            str(self.fragment)
        ).geturl()
