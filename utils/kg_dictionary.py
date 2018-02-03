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

# This file should be in the same directory with source file.
DESCRIPTIONS_FN = 'descriptions.cfg'

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
        session.cookies = load_cookies(args.cookie_file)

        for file_path in args.files:
            can_i_haz_login(session)
            upload_dictionary(session, file_path)


def load_cookies(file_path):
    """Load cookie.txt."""
    cookies = MozillaCookieJar(str(file_path))
    cookies.load()
    return cookies


def can_i_haz_login(session):
    """Check if we are still logged in."""
    page_add = session.get(VOC_ADD_URL)
    if not check_csrf_token(page_add.text):
        exit('Login failed - update your cookies')


def check_csrf_token(page_text):
    """Extract CSRF token from vocadd form."""
    match = re.search("name='csrftoken' value='([^']+)'", page_text)
    return bool(match)


def upload_dictionary(session, file_path):
    """Create dictionary on KG in given Session from specified file."""
    form_data = create_post_data(file_path)

    rq = requests.Request('POST', VOC_ADD_URL, files=form_data)
    resp = session.send(strip_filename_headers(session.prepare_request(rq)))

    find_err = re.search('class=error>(.+)</div>', resp.text)
    # Warning: this is not so reliable.
    if find_err:
        log.error('Dictionary creation from %s failed: %s',
                  file_path, find_err.group(1))
    else:
        log.info('Created %s "%s"', resp.url, form_data['name'])


def create_post_data(file_path):
    """Create dictionary data for HTTP post from file."""

    def prepare_as_text(text):
        """Append dot or else KG will replace last letter of text to it."""
        return text if text.endswith('.') else text + '.'

    def form_fields(content, metadata):
        """Return required for HTTP POST fields.

        :param content: dictionary content as text.
        :param metadata: dict with settings for kg. dictionary:

            * name,
            * description.

        """
        content = prepare_as_text(content)

        log.debug('Text:\n%s', content)
        log.debug('Metadata:\n%s', pformat(dict(metadata.items())))

        return {
            'name': metadata['name'],
            'description': metadata['description'],
            'public': 'public',
            'type': 'texts',
            'words': content,
            'info': '',
            'url': '',
            'submit': 'Добавить',
        }

    log.debug('File: %s', file_path)
    return form_fields(load_text(file_path), get_metadata(file_path))


def load_text(file_path):
    """Get contents of dictionary file."""
    with open(file_path) as fp:
        return fp.read().strip()


def get_metadata(file_path):
    """Read metadata from descriptions.cfg for specified file."""
    desc = ConfigParser()
    descriptions_path = file_path.parent / DESCRIPTIONS_FN
    try:
        desc.read(descriptions_path)
        return desc[file_path.name]
    except KeyError:
        exit(f'Cannot load metadata from {descriptions_path}')


def strip_filename_headers(prep_rq):
    """Fix some shit in PreparedRequest."""
    # It seems that kg doesn't like this field, but requests forces it.
    replaced = re.sub('filename="([a-z]+)"', '', prep_rq.body.decode())
    prep_rq.body = replaced.encode()
    prep_rq.prepare_content_length(prep_rq.body)
    return prep_rq


if __name__ == '__main__':
    main()
