from .node import Node

class Reference(Node):
    def __init__(self, content, url, children=None):
        super().__init__(content, children)
        self.url = url

    def __str__(self):
        return self.content
