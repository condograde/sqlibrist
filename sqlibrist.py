#!/bin/env python
# -*- coding: utf8 -*-
import argparse
from sys import stdout

import yaml

from commands.diff import diff
from commands.init import init
from commands.initdb import initdb
from commands.makemigration import makemigration
from commands.migrate import migrate
from commands.status import status
from commands.test_connection import test_connection

command_list = {
    'test_connection': test_connection,
    'init': init,
    'makemigration': makemigration,
    'migrate': migrate,
    'diff': diff,
    'status': status,
    'initdb': initdb
}

if __name__ == '__main__':

    # todo: implement commands with subparsers
    parser = argparse.ArgumentParser()
    parser.add_argument('command', type=str, choices=command_list.keys())
    parser.add_argument('--config-file', '-f', type=str, default='sqlibrist.yaml')
    parser.add_argument('--config', '-c', type=str, default='default')
    parser.add_argument('--migration', '-m', type=str)
    parser.add_argument('--down', action='store_true')
    parser.add_argument('--empty', action='store_true', default=False)
    parser.add_argument('--dry-run', action='store_true', default=False)
    parser.add_argument('--verbose', '-v', action='store_true', default=False)
    args = parser.parse_args()

    # config
    try:
        with open(args.config_file) as config_file:
            configs = yaml.load(config_file.read())
    except IOError:
        # no config yet
        # todo: make more explicit and allow only creating config file
        current_config = None
        stdout.write(u'No config file found!\n')
    else:
        current_config = configs[args.config]

    command_list[args.command](current_config, args)
