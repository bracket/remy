from flask import Flask, request, url_for, redirect
import re
from markupsafe import escape

from pathlib import Path
import functools

memoize = functools.lru_cache(None)

FILE = Path(__file__).absolute()
HERE = FILE.parent


app = Flask(
    'remy',
    static_url_path = '/static',
    static_folder = HERE / 'static',
    template_folder = HERE / 'templates'
)

notecard_cache = None

@memoize
def vite_url():
    import os
    from remy.url import URL

    vite_url = os.environ.get('REMY_VITE_URL')

    if vite_url is None:
        return None

    return URL(vite_url)


@app.route('/', defaults = { 'path' : '' })
@app.route('/<path:path>')
def root(path):
    if vite_url() is None:
        return app.send_static_file('index.html')
    else:
        full_url = vite_url()._replace(path=path)
        return redirect(full_url.geturl())


def markup_card(card):
    from remy.ast.parse import parse_content
    from remy.ast import Text, Reference, Field

    newline_re = re.compile(r'\r?\n')

    out = [ ]

    for node in parse_content(card.content.strip()):
        if isinstance(node, Text):
            content = escape(node.content)
            content = newline_re.sub('<br/>\n', content)
            out.append(content)
        elif isinstance(node, Reference):
            out.append(format_reference(node))
        elif isinstance(node, Field):
            out.append(format_field(node))
        else:
            out.append(escape(str(node)))

    out.append('<br/><br/>')
    edit_url = url_for('vim', card_label=card.primary_label)
    out.append('<a href="{}" target="_blank">edit</a>'.format(edit_url))

    return ''.join(out)


@app.route('/notecard/<card_label>')
def notecard(card_label):
    card = notecard_cache.find_card_by_label(card_label)
    return markup_card(card)


@app.route('/api')
def api():
    return ('', 204)



@app.route('/api/notecard/<card_label>')
def notecard_js(card_label):
    card = notecard_cache.find_card_by_label(card_label)

    if not card:
        return 404

    return {
        'raw' : card.content
    }


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

        # return r'<a href="{}" onclick="get_card();">{}</a>'.format(target_url, first_line)
        quoted = "'{}'".format(url.netloc)
        out = r'<div class="card" onClick="get_card(this, {});">{}</div>'.format(quoted, first_line)
        print(out)
        return out
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


# @app.route('/vim/<card_label>')
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


def create_app(cache_url):
    global notecard_cache

    if notecard_cache:
        return app

    from remy.url import URL
    from remy.notecard_cache import NotecardCache
    from pathlib import Path

    url = URL(cache_url)

    if not url.scheme:
        url = URL(Path(cache_url).absolute())

    # ('Starting at cache: {}'.format(url.geturl()))
    notecard_cache = NotecardCache(url)

    return app
