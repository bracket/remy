"""
Remy: A notecard system
"""

import json
import setuptools

def main():
    with open('project.json') as fd:
        meta = json.load(fd)

    setuptools.setup(
        name         = meta['name'],
        version      = meta['version'],
        author       = meta['author'],
        author_email = meta['author_email'],
        license      = meta['license'],

        install_requires = [
            'lark',
        ],

        extras_require = {
            'dev' : [
                'flake8',
                'pytest',
                'sphinx',
            ]
        },

        packages = setuptools.find_packages(where='./src'),
        package_dir = { '' : 'src' },
    )

if __name__ == '__main__':
     main()
