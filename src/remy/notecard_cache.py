from .url import URL
from .exceptions import RemyError

class NotecardCache(object):
    def __init__(self, url):
        self.url = URL(url)

        if self.url.scheme != 'file':
            raise RemyError("Currently only local 'file' based NotecardCache's are supported. url: '{}'".format(self.url.geturl()))

        self.__cards_by_label = None
        self.__primary_labels = None
        self.__references = None
        self.__to_primary_label = None
        self.__config_module = None

        self.__field_indexes = { }


    @property
    def config_module(self):
        import importlib.machinery
        import importlib.util

        if self.__config_module is not None:
            return self.__config_module

        config_path = self.url.path / '.remy_config.py'

        loader = importlib.machinery.SourceFileLoader('remy_config', str(config_path))
        spec = importlib.util.spec_from_loader('remy_config', loader )
        config_module = importlib.util.module_from_spec(spec)
        loader.exec_module(config_module)

        self.__config_module = config_module

        return config_module


    def field_index(self, name):
        from remy.notecard_index import NotecardIndex

        name = name.upper()
        index = self.__field_indexes.get(name)

        if index is not None:
            return index

        parser = self.config_module.PARSER_BY_FIELD_NAME[name]
        index = NotecardIndex(self, name, parser)

        self.__field_indexes[name] = index

        return index


    def field_indices(self, field_names):
        """
        Get field indices for multiple field names.
        
        Args:
            field_names: Iterable of field names
        
        Returns:
            Dictionary mapping uppercase field names to NotecardIndex objects.
            Fields that don't exist in the config are silently skipped.
        """
        indices = {}
        for field_name in field_names:
            try:
                indices[field_name.upper()] = self.field_index(field_name)
            except (KeyError, AttributeError):
                # Field doesn't exist in config - skip it
                pass
        return indices


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


    @property
    def primary_labels(self):
        if self.__primary_labels is not None:
            return self.__primary_labels

        primary_labels = frozenset(card.primary_label for card in self.cards_by_label.values())

        self.__primary_labels = primary_labels

        return primary_labels


    @property
    def to_primary_label(self):
        if self.__to_primary_label is not None:
            return self.__to_primary_label

        to_primary_label = {
            label : card.primary_label
            for label, card in self.cards_by_label.items()
        }

        self.__to_primary_label = to_primary_label

        return to_primary_label


    @property
    def references(self):
        from remy.ast.parse import parse_content
        from remy.ast import Reference
        from .groupby import set_groupby

        if self.__references is not None:
            return self.__references


        def reference_iter():
            for label, card in self.cards_by_label.items():
                if label != card.primary_label:
                    continue

                for node in parse_content(card.content):
                    if not isinstance(node, Reference):
                        continue

                    yield (label, node.url)

        references = self.__references = set_groupby(reference_iter())

        return references



    def find_card_by_label(self, label):
        return self.cards_by_label.get(label, None)
