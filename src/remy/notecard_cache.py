from .url import URL
from .exceptions import RemyError

class NotecardCache(object):
    def __init__(self, url):
        self.url = URL(url)
        self.__cards_by_label = None


    @property
    def cards_by_label(self):
        from .notecard import from_url

        if self.__cards_by_label is not None:
            return self.__cards_by_label

        out = { }

        for card in from_url(self.url):
            for label in card.labels:
                if label in out:
                    raise RemyError('duplicated label in cache.  url: {}, label: {}'.format(self.url, label))

                out[label] = card

        self.__cards_by_label = out

        return out
