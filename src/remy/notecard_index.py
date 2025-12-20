from .notecard_cache import NotecardCache
from sortedcontainers import SortedSet
from .exceptions import RemyError

from .groupby import list_groupby

import sys
from typing import Any, Generator, Optional, Tuple

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


    def find(
        self, 
        low: Any = null, 
        high: Any = null, 
        snap: Optional[str] = None
    ) -> Generator[Tuple[Any, str], None, None]:
        """
        Find notecards with field values in the specified range.
        
        Yields tuples of (field_value, notecard_label) for all notecards whose
        field values fall within the range [low, high], inclusive. If only `low`
        is specified, searches for an exact match (high defaults to low).
        
        Args:
            low: The lower bound of the search range. If null (default), uses the
                 minimum possible value. The type must be compatible with the
                 field_parser used to index this field.
            high: The upper bound of the search range. If null (default) and low
                  is specified, high defaults to low (exact match search). If both
                  are null, searches the entire index.
            snap: Controls boundary behavior when the exact bound value is not in
                  the index:
                  - None (default): No adjustment; starts from the first value >= low
                  - 'soft': Includes one value before low if it exists, extending the
                    range downward by one entry
                  - 'hard': Rounds down to the nearest value that has multiple entries
                    with the same key (all entries sharing the low key value are
                    included)
        
        Yields:
            Tuples of (field_value, notecard_label) for each match in the range
        """
        if low is not null:
            low_key = (id(type(low)), low)
        else:
            low_key = (0,)

        if high is not null:
            high_key = (id(type(high)), high)
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
