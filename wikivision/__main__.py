#!/usr/bin/python
import argparse

from wikivision.app import app


def get_parser():
    parser = argparse.ArgumentParser(
        prog='python -m wikivision',
        description="Visualize Wikipedia article revision histories.",
    )
    parser.add_argument('article_slug', nargs='?')
    return parser


if __name__ == '__main__':
    parser = get_parser()
    args = parser.parse_args()
    app.run(debug=True)
