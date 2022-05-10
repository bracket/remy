class Language(object):
    def nullity(self):
        raise NotImplementedError()


    def derivative(self, token):
        raise NotImplementedError()


class null(Language):
    def __new__(cls):
        return null


    def nullity():
        return null


    def derivative(token):
        return null


    def parse(tokens, offset):
        raise StopIteration


class epsilon(Language):
    def __new__(cls):
        return epsilon


    def nullity():
        return epsilon


    def derivative(token):
        return null


    def parse(tokens, offset):
        yield (offset, { 'children' : [ ] })


class Terminal(Language):
    def __init__(self, terminal_type):
        self.terminal_type = terminal_type


    def nullity(self):
        return null


    def derivative(self, token):
        if token[0] == self.token_type:
            return epsilon
        else:
            return null


    def parse(self, tokens, offset):
        token = tokens[offset]

        if token[0] == self.terminal_type:
            yield (offset + 1, { 'children' : [ token ] })


class Union(Language):
    def __init__(self, left, right):
        self.left = left
        self.right = right


    def nullity(self):
        if self.left.nullity() is epsilon:
            return epsilon

        if self.right.nullity() is epsilon:
            return epsilon

        return null


    def derivative(self, token):
        return union(
            self.left.derivative(token),
            self.right.derivative(token)
        )


    def parse(self, tokens, offset):
        yield from self.left.parse(tokens, offset)
        yield from self.right.parse(tokens, offset)


class Concat(Language):
    def __init__(self, left, right):
        self.left = left
        self.right = right


    def nullity(self):
        if self.left.nullity() is null:
            return null

        if self.right.nullity() is null:
            return null

        return epsilon


    def derivative(self, token):
        left = self.left.derivative(token)
        left_nullity = self.left.nullity()

        if left_nullity is null:
            return concat(left, self.right)

        return union(
            concat(left, self.right),
            self.right.derivative(token),
        )


    def parse(self, tokens, offset):
        for (left_offset, left_tree) in self.left.parse(tokens, offset):
            for (right_offset, right_tree) in self.right.parse(tokens, left_offset):
                out = { 'children' : left_tree['children'] + right_tree['children'] }
                yield (right_offset, out)


class Repeat(Language):
    def __init__(self, language):
        self.language = language


    def nullity(self):
        return epsilon


    def derivative(self, token):
        'D_t(A*) = D_t(A)A*'

        pass


    def parse(self, tokens, offset):
        pass


class Named(Language):
    def __init__(self, name, language):
        self.name = name
        self.language = language


    def nullity(self):
        return self.language.nullity()


    def derivative(self, token):
        pass


    def parse(self, tokens, offset):
        for (new_offset, tree) in self.language.parse(tokens, offset):
            tree['name'] = self.name
            yield (new_offset, { 'children' : [ tree ] })


def terminal(terminal_type):
    return Terminal(terminal_type)


def concat(left, right, *args):
    if args:
        right = concat(right, *args)

    if left is null:
        return null

    if right is null:
        return null

    if left is epsilon:
        return right

    if right is epsilon:
        return left

    if isinstance(left, Concat):
        return concat(left.left, concat(left.right, right))

    return Concat(left, right)


def union(left, right, *args):
    if args:
        right = union(right, *args)

    if left is null:
        return right

    if right is null:
        return left

    if left == right:
        return left

    if isinstance(left, Union):
        return union(left, union(left.right, right))

    return Union(left, right)


def named(name, language):
    if language is null:
        return null

    return Named(name, language)


def optional(language):
    return union(
        language,
        epsilon
    )
