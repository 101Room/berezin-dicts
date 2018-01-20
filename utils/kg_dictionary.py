#!/usr/bin/env python
"""Create dictionaries on klavogonki.ru."""

import argparse
import logging
from configparser import ConfigParser
from pathlib import Path
from pprint import pformat
from os import listdir

log = logging.getLogger()

METADATA_FN = 'descriptions.cfg'
SETTINGS_FN = 'settings.cfg'


def parse_args():
    """Parse command line arguments."""

    def _get_path(value):
        path = Path(value)
        if path.exists():
            return path
        else:
            raise argparse.ArgumentTypeError(f'{value} not found')

    parser = argparse.ArgumentParser()

    g_source = parser.add_argument_group('Select source') \
        .add_mutually_exclusive_group(required=True)
    g_source.add_argument('-f', dest='file_path', type=_get_path)
    g_source.add_argument('-d', dest='dir_path', type=_get_path)

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

    settings = get_settings(Path(__file__).parent / SETTINGS_FN)

    if args.file_path:
        log.debug('From file %s', args.file_path)
        create_dictionary(read_words(args.file_path), get_metadata(args.file_path))
    else:
        for file_name in listdir(args.dir_path):
            file_path = args.dir_path / file_name
            log.debug('From file %s', file_path)
            create_dictionary(read_words(file_path), get_metadata(file_path))


def get_settings(config_path):
    """Return settings for script (nested dict)."""
    cfg = ConfigParser()
    cfg.read(config_path)
    return cfg


def read_words(file_path):
    """Return list of words from file."""
    with open(file_path) as fp:
        return fp.read().split()


def get_metadata(file_path):
    """Read metadata from descriptions.cfg for specified file."""
    desc = ConfigParser()
    desc.read(file_path.parent / METADATA_FN)
    return desc[file_path.name]


def create_dictionary(words, metadata):
    """Create dictionary.

    :param words: words list.
    :param metadata: dict with settings for kg. dictionary:

        * name,
        * description.
    """
    log.debug('Words list: %s', words)
    log.debug('Metadata: %s', pformat(dict(metadata.items())))


if __name__ == '__main__':
    main()
