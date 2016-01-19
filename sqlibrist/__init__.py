# -*- coding: utf8 -*-
import argparse

from sqlibrist.commands.diff import diff
from sqlibrist.commands.init import init
from sqlibrist.commands.initdb import initdb
from sqlibrist.commands.makemigration import makemigration
from sqlibrist.commands.status import status
from sqlibrist.commands.test_connection import test_connection

from sqlibrist.commands.migrate import migrate
from sqlibrist.helpers import SqlibristException, handle_exception


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='store_true', default=False)
    parser.add_argument('--config-file', '-f',
                        help=u'Config file, default is sqlibrist.yaml',
                        type=str,
                        default='sqlibrist.yaml')
    parser.add_argument('--config', '-c',
                        help=u'Config name in config file, default is "default"',
                        type=str,
                        default='default')

    subparsers = parser.add_subparsers()

    # test_connection
    test_connection_parser = subparsers.add_parser('test_connection',
                                                   help=u'Test DB connection')
    test_connection_parser.set_defaults(func=test_connection)

    # init
    init_parser = subparsers.add_parser('init',
                                        help=u'Init directory structure')
    init_parser.set_defaults(func=init)

    # initdb
    initdb_parser = subparsers.add_parser('initdb',
                                          help=u'Create DB table for migrations tracking')
    initdb_parser.set_defaults(func=initdb)

    # makemigrations
    makemigration_parser = subparsers.add_parser('makemigration',
                                                 help='Create new migration')
    makemigration_parser.set_defaults(func=makemigration)
    makemigration_parser.add_argument('--inplace',
                                      help=u'Do not cascadely DROP-CREATE changed entities and their dependencies',
                                      action='store_true',
                                      default=False)
    makemigration_parser.add_argument('--empty',
                                      help=u'Create migration with empty up.sql for manual instructions',
                                      action='store_true',
                                      default=False)
    makemigration_parser.add_argument('--name', '-n',
                                      help=u'Optional migration name',
                                      type=str,
                                      default='')
    makemigration_parser.add_argument('--dry-run',
                                      help=u'Do not save migration',
                                      action='store_true',
                                      default=False)

    # migrate
    migrate_parser = subparsers.add_parser('migrate',
                                           help=u'Apply pending migrations')
    migrate_parser.set_defaults(func=migrate)
    migrate_parser.add_argument('--fake',
                                help=u'Mark pending migrations as applied',
                                action='store_true',
                                default=False)
    migrate_parser.add_argument('--dry-run',
                                help=u'Do not make actual changes to the DB',
                                action='store_true',
                                default=False)
    migrate_parser.add_argument('--migration', '-m',
                                help=u'Apply up to given migration number',
                                type=str)
    migrate_parser.add_argument('--revert',
                                help=u'Unapply last migration',
                                action='store_true')

    # diff
    diff_parser = subparsers.add_parser('diff', help=u'Show changes to schema')
    diff_parser.set_defaults(func=diff)

    # status
    status_parser = subparsers.add_parser('status',
                                          help=u'Show unapplied migrations')
    status_parser.set_defaults(func=status)

    args = parser.parse_args()

    try:
        args.func(args)
    except SqlibristException as e:
        handle_exception(e)
