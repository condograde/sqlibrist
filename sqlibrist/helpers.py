# -*- coding: utf8 -*-
from __future__ import print_function

import argparse
import glob
import hashlib
import os
import re
from json import loads, dumps

from sqlibrist.engines import Postgresql, MySQL

ENGINE_POSTGRESQL = 'pg'
ENGINE_MYSQL = 'mysql'

ENGINES = {
    ENGINE_POSTGRESQL: Postgresql,
    ENGINE_MYSQL: MySQL
}


class SqlibristException(Exception):
    pass


class CircularDependencyException(SqlibristException):
    pass


class UnknownDependencyException(SqlibristException):
    pass


class BadConfig(SqlibristException):
    pass


class ApplyMigrationFailed(SqlibristException):
    pass


class MigrationIrreversible(SqlibristException):
    pass


class LazyConfig(object):
    def __init__(self, args):
        self.args = args

    def load_config(self):
        import yaml
        from yaml.scanner import ScannerError

        try:
            with open(self.args.config_file) as config_file:
                configs = yaml.load(config_file.read())
        except IOError:
            raise BadConfig('No config file %s found!' % self.args.config_file)
        except ScannerError:
            raise BadConfig('Bad config file syntax')
        else:
            try:
                self._dict = configs[self.args.config]
            except KeyError:
                raise BadConfig('No config named %s found!' % self.args.config)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __getitem__(self, key):
        try:
            return self._dict[key]
        except AttributeError:
            self.load_config()
            return self[key]

    def __repr__(self):
        try:
            return self._dict
        except AttributeError:
            self.load_config()
            return repr(self)


def get_engine(config, connection=None):
    try:
        return ENGINES[config['engine']](config, connection)
    except KeyError:
        raise BadConfig('DB engine not selected in config or wrong engine '
                        'name (must be one of %s)' % ','.join(ENGINES.keys()))


def get_last_schema():
    schemas = sorted(glob.glob('migrations/*'))
    if schemas:
        with open(os.path.join(schemas[-1], 'schema.json'), 'r') as f:
            schema = loads(f.read())
    else:
        schema = {}
    return schema


def extract_reqs(lines):
    for line in lines:
        if line.strip().startswith('--REQ'):
            _, requirement = line.split()
            yield requirement


def extract_up(lines):
    on = False
    for line in lines:
        if line.strip().startswith('--UP'):
            on = True
        elif line.strip().startswith('--DOWN'):
            raise StopIteration
        elif on:
            yield line.rstrip()


def extract_down(lines):
    on = False
    for line in lines:
        if line.strip().startswith('--DOWN'):
            on = True
        elif on:
            yield line.rstrip()


def init_item(directory, filename):
    with open(os.path.join(directory, filename), 'r') as f:
        lines = f.readlines()

    filename = '/'.join(directory.split('/')[1:] + [filename[:-4]])
    requires = list(extract_reqs(lines))
    up = list(extract_up(lines))
    down = list(extract_down(lines))
    _hash = hashlib.md5(re.sub(r'\s{2,}', '', ''.join(up))).hexdigest()

    return (filename,
            {'hash': _hash,
             'name': filename,
             'requires': requires,
             'required': [],
             'up': up,
             'down': down})


def schema_collector():
    files_generator = os.walk('schema')
    for directory, subdirectories, files in files_generator:
        for filename in files:
            if filename.endswith('.sql'):
                yield init_item(directory, filename)


def check_for_circular_dependencies(schema, name, metadata, stack=()):
    if name in stack:
        raise CircularDependencyException(stack + (name,))
    for requires in metadata['requires']:
        check_for_circular_dependencies(schema,
                                        requires,
                                        schema[requires],
                                        stack + (name,))


def calculate_cumulative_degree(schema, name, metadata, degree=0):
    return len(metadata['requires']) \
           + sum([calculate_cumulative_degree(schema,
                                              requirement,
                                              schema[requirement])
                  for requirement in metadata['requires']])


def get_current_schema():
    schema = dict(schema_collector())

    item_names = schema.keys()

    for name, metadata in schema.items():
        for requirement in metadata['requires']:
            if requirement not in item_names:
                raise UnknownDependencyException((requirement, name))

            schema[requirement]['required'].append(name)
    for name, metadata in schema.items():
        check_for_circular_dependencies(schema, name, metadata)
        metadata['degree'] = calculate_cumulative_degree(schema, name, metadata)
    return schema


def compare_schemas(last_schema, current_schema):
    last_set = set(last_schema.keys())
    current_set = set(current_schema.keys())

    added = current_set - last_set
    removed = last_set - current_set
    changed = [item
               for item in last_set.intersection(current_set)
               if last_schema[item]['hash'] != current_schema[item]['hash']]

    return added, removed, changed


def save_migration(schema, plan_up, plan_down, suffix=''):
    migration_name = '%04.f%s' % (len(glob.glob('migrations/*')) + 1, suffix)
    dirname = os.path.join('migrations', migration_name)
    print('Creating new migration %s' % migration_name)
    os.mkdir(dirname)
    schema_filename = os.path.join(dirname, 'schema.json')
    with open(schema_filename, 'w') as f:
        f.write(dumps(schema, indent=2))

    plans = (
        ('up.sql', plan_up),
        ('down.sql', plan_down),
    )
    for plan_name, instructions in plans:
        with open(os.path.join(dirname, plan_name), 'w') as f:
            for item in instructions:
                f.write('-- begin --\n')
                f.write(('\n'.join(map(lambda s: s.encode('utf8'),
                                       item))).strip())
                f.write('\n')
                f.write('-- end --\n')
                f.write('\n\n')


def mark_affected_items(schema, name):
    schema[name]['status'] = 'changed'
    for required in schema[name]['required']:
        mark_affected_items(schema, required)


def handle_exception(e):
    if isinstance(e, CircularDependencyException):
        print('Circular dependency:')
        print('  %s' % ' >\n  '.join(e.message))
    elif isinstance(e, UnknownDependencyException):
        print('Unknown dependency %s at %s' % e.message)
    elif isinstance(e, (BadConfig, MigrationIrreversible)):
        print(e.message)


def get_command_parser(parser=None):
    from sqlibrist.commands.diff import diff
    from sqlibrist.commands.init import init
    from sqlibrist.commands.initdb import initdb
    from sqlibrist.commands.makemigration import makemigration
    from sqlibrist.commands.status import status
    from sqlibrist.commands.test_connection import test_connection
    from sqlibrist.commands.migrate import migrate
    from sqlibrist.commands.info import info

    _parser = parser or argparse.ArgumentParser()
    _parser.add_argument('--config-file', '-f',
                         help='Config file, default is sqlibrist.yaml',
                         type=str,
                         default=os.environ.get('SQLIBRIST_CONFIG_FILE',
                                                'sqlibrist.yaml'))
    _parser.add_argument('--config', '-c',
                         help='Config name in config file, '
                              'default is "default"',
                         type=str,
                         default=os.environ.get('SQLIBRIST_CONFIG', 'default'))

    subparsers = _parser.add_subparsers(parser_class=argparse.ArgumentParser)

    # print info
    print_info_parser = subparsers.add_parser('info',
                                              help='Print sqlibrist info')
    print_info_parser.add_argument('--verbose', '-v',
                                   action='store_true', default=False)
    print_info_parser.set_defaults(func=info)

    # test_connection
    test_connection_parser = subparsers.add_parser('test_connection',
                                                   help='Test DB connection')
    test_connection_parser.add_argument('--verbose', '-v',
                                        action='store_true', default=False)
    test_connection_parser.set_defaults(func=test_connection)

    # init
    init_parser = subparsers.add_parser('init',
                                        help='Init directory structure')
    init_parser.add_argument('--verbose', '-v',
                             action='store_true', default=False)
    init_parser.set_defaults(func=init)

    # initdb
    initdb_parser = subparsers.add_parser('initdb',
                                          help='Create DB table for '
                                               'migrations tracking')
    initdb_parser.add_argument('--verbose', '-v',
                               action='store_true', default=False)
    initdb_parser.set_defaults(func=initdb)

    # makemigrations
    makemigration_parser = subparsers.add_parser('makemigration',
                                                 help='Create new migration')
    makemigration_parser.set_defaults(func=makemigration)
    makemigration_parser.add_argument('--verbose', '-v',
                                      action='store_true', default=False)

    makemigration_parser.add_argument('--empty',
                                      help='Create migration with empty up.sql '
                                           'for manual instructions',
                                      action='store_true',
                                      default=False)
    makemigration_parser.add_argument('--name', '-n',
                                      help='Optional migration name',
                                      type=str,
                                      default='')
    makemigration_parser.add_argument('--dry-run',
                                      help='Do not save migration',
                                      action='store_true',
                                      default=False)

    # migrate
    migrate_parser = subparsers.add_parser('migrate',
                                           help='Apply pending migrations')
    migrate_parser.set_defaults(func=migrate)
    migrate_parser.add_argument('--verbose', '-v',
                                action='store_true', default=False)
    migrate_parser.add_argument('--fake',
                                help='Mark pending migrations as applied',
                                action='store_true',
                                default=False)
    migrate_parser.add_argument('--dry-run',
                                help='Do not make actual changes to the DB',
                                action='store_true',
                                default=False)
    migrate_parser.add_argument('--migration', '-m',
                                help='Apply up to given migration number',
                                type=str)
    migrate_parser.add_argument('--revert', '-r',
                                help='Unapply last migration',
                                action='store_true')

    # diff
    diff_parser = subparsers.add_parser('diff', help='Show changes to schema')
    diff_parser.set_defaults(func=diff)
    diff_parser.add_argument('--verbose', '-v',
                             action='store_true', default=False)

    # status
    status_parser = subparsers.add_parser('status',
                                          help='Show unapplied migrations')
    status_parser.add_argument('--verbose', '-v',
                               action='store_true', default=False)
    status_parser.set_defaults(func=status)
    return _parser
