from flask import Flask, request, url_for
import click
from markupsafe import escape

app = Flask('remy')
notecard_cache = None

@app.route('/')
def root():
    card = notecard_cache.find_card_by_label('main')

    return '''
        <html>
            <title>main</title>
            <body>
                {}
            </body>
        </html>
    '''.format(escape(card.content))


@app.route('/notecard/<card_label>')
def notecard(card_label):
    from remy.ast.parse import parse_content
    from remy.ast import Text, Reference, Field

    card = notecard_cache.find_card_by_label(card_label)

    out = [ ]

    for node in parse_content(card.content.strip()):
        if isinstance(node, Text):
            content = escape(node.content)
            content = '<br/>\n'.join(content.splitlines())
            out.append(content)
        elif isinstance(node, Reference):
            out.append(format_reference(node))
            out.append('<br/>')
        elif isinstance(node, Field):
            out.append(format_field(node))
        else:
            out.append(escape(str(node)))

    out.append('<br/><br/>')
    edit_url = url_for('vim', card_label=card_label)
    out.append('<a href="{}" target="_blank">edit</a>'.format(edit_url))

    return ''.join(out)


def format_reference(ref):
    from remy.url import URL
    from remy.ast.parse import parse_content
    from remy.ast import Text
    from urllib.parse import quote as url_escape

    url = ref.url

    if url.scheme == 'note':
        card = notecard_cache.find_card_by_label(url.netloc)

        text = [ n.content.strip() for n in parse_content(card.content) if isinstance(n, Text) ]
        text = next((t for t in text if t), url.netloc)

        first_line = text.splitlines()[0]

        target_url = url_for('notecard', card_label=url.netloc)

        return '<a href="{}">{}</a>'.format(target_url, first_line)
    elif url.scheme == 'rfc822msgid':
        message_id = url_escape(url.netloc)
        target_url = 'https://mail.google.com/mail/u/0/#search/rfc822msgid%3A{}'.format(message_id)

        return '<a href="{}" target="_blank">gmail</a>'.format(target_url)


    return url.geturl()


def format_field(field):
    return '<b>{}</b>:{}<br/>'.format(
        escape(field.label.strip()),
        escape(field.value.strip())
    )

    label = field.label.strip()
    content = field.content.strip()

    # return '<b>{}</b>: {}'.format(field.label.strip()


@app.route('/vim/<card_label>')
def vim(card_label):
    import subprocess as sp

    card = notecard_cache.find_card_by_label(card_label)
    url = card.source_url

    if url.scheme != 'file':
        raise RuntimeError("Can't open url in terminal with non-'file' scheme. url:'{}'".format(url.geturl()))

    # command = ['gterm', '--geometry=157x77-3+31' , '--', 'vim' ]
    command = [
        'gnome-terminal', '--geometry=157x77+963+31',
        '--',
        'vim',
        str(url.path),
        "+{}|normal zt".format(int(url.fragment) + 1) if url.fragment else '',
    ]

    sp.run(command)

    return ' '.join(command)

    # sp.run(['gterm', '--geometry=157x77-3+31' ]
    return card.source_url.geturl()


@click.command
@click.option('--cache', help='Location of Remy notecard cache.', required=True)
def main(cache):
    global notecard_cache

    from remy.url import URL
    from remy.notecard_cache import NotecardCache
    from pathlib import Path

    url = URL(cache)

    if not url.scheme:
        url = URL(Path(cache).absolute())

    print('Starting at cache: {}'.format(url.geturl()))
    notecard_cache = NotecardCache(url)

    app.run()


if __name__ == '__main__':
    main(auto_envvar_prefix='REMY')
