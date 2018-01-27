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

    parser.add_argument('-f', dest='files', type=_get_path, nargs='+', required=True)
    parser.add_argument('-c', dest='cookie_file', type=_get_path, required=True,
                        help='Path to cookies.txt')

    return parser.parse_args()


def init_logging():
    """Initialize logging."""
    logging.basicConfig(
        format='[%(levelname).1s] %(module)s: %(message)s',
        level=logging.INFO,
    )


def main():
    """Entry point."""
    args = parse_args()
    init_logging()

    with requests.session() as session:
        session.cookies = load_cookie(args.cookie_file)

        for file_path in args.files:
            form_data = create_dictionary_data(file_path)

            rq = requests.Request('POST', VOC_ADD_URL, files=form_data)
            prep_rq = session.prepare_request(rq)
            # It seems that kg doesn't like this field, but requests forces it.
            prep_rq.body = re.sub('filename="([a-z]+)"', '', prep_rq.body.decode()).encode()
            prep_rq.prepare_content_length(prep_rq.body)
            resp = session.send(prep_rq)

            find_err = re.search('class=error>(.+)</div>', resp.text)
            if find_err:
                log.error('Dictionary creation from %s failed: %s', file_path, find_err.group(1))
            else:
                log.info('Created %s "%s"', resp.url, form_data['name'])


def read_words(file_path):
    """Return list of words from file."""
    with open(file_path) as fp:
        return fp.read().strip()


def get_metadata(file_path):
    """Read metadata from descriptions.cfg for specified file."""
    desc = ConfigParser()
    description_fn = file_path.parent / METADATA_FN
    try:
        desc.read(description_fn)
        return desc[file_path.name]
    except KeyError:
        raise ValueError('Cannot load metadata from "descriptions.cfg"')


def create_dictionary_data(file_path):
    """Create dictionary data from file."""

    def form_data(words, metadata):
        """Return data suitable for HTTP POST.

        :param words: words list.
        :param metadata: dict with settings for kg. dictionary:

            * name,
            * description.
        """
        log.debug('Words list:\n%s', words)
        log.debug('Metadata: %s', pformat(dict(metadata.items())))

        return {
            'name': metadata['name'],
            'description': metadata['description'],
            'public': 'public',
            'type': 'texts',
            'words': words + '.',
            'info': '',
            'url': '',
            'submit': 'Добавить',
        }

    log.debug('File: %s', file_path)
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
