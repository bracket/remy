import click
from .app import create_app

@click.command
@click.option('--cache', help='Location of Remy notecard cache.', required=True)
@click.option('--host', help='Flask host to serve from', required=False)
def main(cache, host=None):
    app = create_app(cache)
    app.run(host=host)


if __name__ == '__main__':
    main(auto_envvar_prefix='REMY')
