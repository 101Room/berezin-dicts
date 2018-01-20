#!/usr/bin/env python
"""Create dictionaries on klavogonki.ru."""

import argparse
import logging
import re
from configparser import ConfigParser
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from pprint import pformat
from urllib.parse import urljoin

import requests

log = logging.getLogger()

METADATA_FN = 'descriptions.cfg'

BASE_URL = 'http://klavogonki.ru/'
VOC_ADD_URL = urljoin(BASE_URL, '/vocs/add')


def parse_args():
    """Parse command line arguments."""

    def _get_path(value):
        path = Path(value)
        if path.exists():
            return path
        else:
            raise argparse.ArgumentTypeError(f'{value} not found')

    parser = argparse.ArgumentParser()

    parser.add_argument('-f', dest='files', type=_get_path, nargs='+')
    parser.add_argument('-c', dest='cookie_file', type=_get_path, required=True,
                        help='Path to cookies.txt')

    return parser.parse_args()


def init_logging():
    """Initialize logging."""
    logging.basicConfig(
        format='[%(levelname).1s] %(message)s',
        level=logging.DEBUG,
    )


def main():
    """Entry point."""
    args = parse_args()
    init_logging()

    with requests.session() as session:
        session.cookies = load_cookie(args.cookie_file)

        for file_path in args.files:
            # TODO: saving doesn't work now
            page_add = session.get(VOC_ADD_URL)
            payload = create_dictionary_data(file_path)
            payload.update(csrftoken=find_csrf_token(page_add.text))
            rs = session.post(VOC_ADD_URL, files=payload)
            log.info('Created %s', rs.url)


def read_words(file_path):
    """Return list of words from file."""
    with open(file_path) as fp:
        return fp.read().split()


def get_metadata(file_path):
    """Read metadata from descriptions.cfg for specified file."""
    desc = ConfigParser()
    desc.read(file_path.parent / METADATA_FN)
    return desc[file_path.name]


def create_dictionary_data(file_path):
    """Create dictionary data from file."""

    def form_data(words, metadata):
        """Return data suitable for HTTP POST.

        :param words: words list.
        :param metadata: dict with settings for kg. dictionary:

            * name,
            * description.
        """
        log.debug('Words list: %s', words)
        log.debug('Metadata: %s', pformat(dict(metadata.items())))

        return {
            'name': metadata['name'],
            'description': metadata['description'],
            'public': 'private',
            'type': 'words',
            'words': '\n'.join(words),
        }

    log.debug('File %s', file_path)
    return form_data(read_words(file_path), get_metadata(file_path))


def load_cookie(file_path):
    """Load cookie.txt."""
    cookie = MozillaCookieJar(str(file_path))
    cookie.load()
    return cookie


def find_csrf_token(page_text):
    """Extract CSRF token from vocadd form."""
    match = re.search("name='csrftoken' value='([^']+)'", page_text)
    if match:
        return match.group(1)
    else:
        raise ValueError('CSRF token not found')


if __name__ == '__main__':
    main()
