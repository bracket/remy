from pprint import pprint

def test_query_grammar():
    import re

    from remy.grammar import expand_grammar
    from remy.query.grammar import token_grammar

    for k, r in expand_grammar(token_grammar(False)).items():
        try:
            re.compile(r)
        except:
            assert False, f"Failed to compile expression for '{k}': '{r}'"


def test_query_tokenizer():
    from remy.query.grammar import tokenize_query

    queries = {
        r'()' : [
            ('lparen', '('),
            ('rparen', ')'),
        ],

        r'(a)' : [
            ('lparen', '('),
            ('identifier', 'a'),
            ('rparen', ')'),
        ],

        r'(a:Weasel { value: "beaver is the \"value\"" })' : [
            ('lparen', '('),
            ('identifier', 'a'),
            ('colon', ':'),
            ('identifier', 'Weasel'),
            ('ws', ' '),
            ('lbrace', '{'),
            ('ws', ' '),
            ('identifier', 'value'),
            ('colon', ':'),
            ('ws', ' '),
            ('literal', r'"beaver is the \"value\""'),
            ('ws', ' '),
            ('rbrace', '}'),
            ('rparen',  ')'),
        ],

        r'(a:Weasel { key_one: 2, key_two: 3.14e3 })-[]->()' : [
            ('lparen', '('),
            ('identifier', 'a'),
            ('colon', ':'),
            ('identifier', 'Weasel'),
            ('ws', ' '),
            ('lbrace', '{'),
            ('ws', ' '),
            ('identifier', 'key_one'),
            ('colon', ':'),
            ('ws', ' '),
            ('literal', '2'),
            ('comma', ','),
            ('ws', ' '),
            ('identifier', 'key_two'),
            ('colon', ':'),
            ('ws', ' '),
            ('literal', '3.14e3'),
            ('ws', ' '),
            ('rbrace', '}'),
            ('rparen', ')'),
            ('hyphen', '-'),
            ('lbracket', '['),
            ('rbracket', ']'),
            ('hyphen', '-'),
            ('rangle', '>'),
            ('lparen', '('),
            ('rparen', ')')
        ],
    }

    for query, tokenized in queries.items():
        assert list(tokenize_query(query)) == tokenized


def test_payer():
    from remy.query.payer import null, epsilon, terminal
    from remy.query.payer import union, Union
    from remy.query.payer import concat, Concat


    assert null() is null
    assert epsilon() is epsilon
    assert null.nullity() is null
    assert epsilon.nullity() is epsilon

    assert terminal('lparen').nullity() is null


def test_query_parser():
    from remy.query.parser import parse_query

    queries = {
        '()' : [ ],
        '(a)' : [ ],
        '(a:Weasel)' : [ ],
    }

    print()

    for query, parsed in queries.items():
        print(query)
        print()
        pprint(parse_query(query))
        print()
        # assert parse_query(query) == parsed
