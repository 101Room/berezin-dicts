#!/usr/bin/python
"""Remove repeated whitespaces and normalize newlines."""

import argparse
import re

def read_source(file_path):
    with open(file_path, 'r') as fp:
        return fp.readlines()


def save(file_path, lines):
    with open(file_path, 'w') as fp:
        fp.writelines(lines)


def normalize(line):
    return re.sub('\s+', ' ', line.strip()) + '\n'


def main(args):
    for file_path in args:
        lines = read_source(file_path)
        save(file_path, map(normalize, lines))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='+')
    main(parser.parse_args().files)

