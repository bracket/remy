from remy.util import generate_unique_label


def test_unique_label():
    labels = { generate_unique_label() for _ in range(3) }

    for l in sorted(labels):
        print(l)


    assert len(labels) == 3
