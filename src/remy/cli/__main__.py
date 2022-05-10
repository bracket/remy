import click

notecard_cache = None

@click.command
@click.option('--cache', help='Location of Remy notecard cache.', required=True)
def main(cache):
    from remy import NotecardCache
    from remy.url import URL
    from pathlib import Path
    from remy.ast.parse import parse_content

    global notecard_cache

    url = URL(cache)

    if not url.scheme:
        url = URL(Path(cache))

    notecard_cache = NotecardCache(url)

    for label, card in sorted(notecard_cache.cards_by_label.items()):
        print(list(parse_content(card.content)))

if __name__ == '__main__':
    main(auto_envvar_prefix='REMY')
