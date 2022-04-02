from .node import Node

class Field(Node):
    def __init__(self, content, label, value, children=None):
        super().__init__(content, children)

        self.label = label
        self.value = value
