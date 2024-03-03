import click
from .app import create_app

@click.command
@click.option('--cache', help='Location of Remy notecard cache.', required=True)
def main(cache):
    app = create_app(cache)
    app.run()


if __name__ == '__main__':
    main(auto_envvar_prefix='REMY')
