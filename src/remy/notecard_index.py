from .notecard_cache import NotecardCache
from sortedcontainers import SortedSet
from .exceptions import RemyError

from groupby import list_groupby

import sys

null = object()

class NotecardIndex(object):
    def __init__(self, notecard_cache, field_name, field_parser):
        self.notecard_cache = notecard_cache
        self.field_name = field_name.upper()
        self.field_parser = field_parser

        self.__index = None
        self.__inverse = None


    @property
    def index(self):
        from remy.ast.parse import parse_content
        from remy.ast import Field

        if self.__index is not None:
            return self.__index

        index = SortedSet()
        name, parser = self.field_name, self.field_parser

        for label, card in self.notecard_cache.cards_by_label.items():
            if label != card.primary_label:
                continue

            for node in parse_content(card.content):
                if not isinstance(node, Field):
                    continue

                if node.label.upper() != name:
                    continue

                for key in self.field_parser(node.value):
                    key = (id(type(key)), key)
                    index.add((key, label))

        self.__index = index

        return index


    @property
    def inverse(self):
        if self.__inverse is not None:
            return self.__inverse

        self.__inverse = list_groupby((label, value) for (_, value), label in self.index)

        return self.__inverse


    def find(self, low = null, high=null, snap=None):
        if low is not null:
            low_key = (id(type(low)), low)
        else:
            low_key = (0,)

        if high is not null:
            high_key = (id(type(high)), high)
        elif low is not null:
            high_key = low_key
        else:
            high_key = (sys.maxsize, )

        low_index = self.index.bisect_left((low_key,))

        if snap is not None:
            if snap == 'soft':
                low_index = max(0, low_index - 1)
            elif snap == 'hard':
                low_index = max(0, low_index - 1)
                key, label = self.index[low_index]
                low_index = self.index.bisect_left((key,))
            else:
                raise RemyError("snap must be one of None, 'soft', or 'hard', snap: {}".format(repr(snap)))


        for key, label in  self.index.islice(low_index):
            if key > high_key:
                return

            yield (key[1], label)
