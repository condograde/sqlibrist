# -*- coding: utf8 -*-
from __future__ import print_function
import argparse
import glob
import hashlib
import os
import re
from json import loads, dumps

from sqlibrist.engines import Postgresql


ENGINES = {
    'pg': Postgresql
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


def get_config(args):
    import yaml
    from yaml.scanner import ScannerError

    try:
        with open(args.config_file) as config_file:
            configs = yaml.load(config_file.read())
    except IOError:
        raise BadConfig('No config file %s found!' % args.config_file)
    except ScannerError:
        raise BadConfig('Bad config file syntax')
    else:
        try:
            return configs[args.config]
        except KeyError:
            raise BadConfig('No config named %s found!' % args.config)


def get_engine(config):
    try:
        return ENGINES[config['engine']](config)
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


def print_version(_):
    from sqlibrist import VERSION
    print(VERSION)


def get_command_parser(parser=None):
    from sqlibrist.commands.diff import diff_command
    from sqlibrist.commands.init import init_command
    from sqlibrist.commands.initdb import initdb_command
    from sqlibrist.commands.makemigration import makemigration_command
    from sqlibrist.commands.status import status_command
    from sqlibrist.commands.test_connection import test_connection_command
    from sqlibrist.commands.migrate import migrate_command

    _parser = parser or argparse.ArgumentParser()
    _parser.add_argument('--verbose', '-V', action='store_true', default=False)
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

    # print version
    test_connection_parser = subparsers.add_parser('version',
                                                   help='Print sqlibrist version')
    test_connection_parser.set_defaults(func=print_version)

    # test_connection
    test_connection_parser = subparsers.add_parser('test_connection',
                                                   help='Test DB connection')
    test_connection_parser.set_defaults(func=test_connection_command)

    # init
    init_parser = subparsers.add_parser('init',
                                        help='Init directory structure')
    init_parser.set_defaults(func=init_command)

    # initdb
    initdb_parser = subparsers.add_parser('initdb',
                                          help='Create DB table for '
                                               'migrations tracking')
    initdb_parser.set_defaults(func=initdb_command)

    # makemigrations
    makemigration_parser = subparsers.add_parser('makemigration',
                                                 help='Create new migration')
    makemigration_parser.set_defaults(func=makemigration_command)

    # todo: not implemented
    # makemigration_parser.add_argument('--inplace',
    #                                   help=u'Do not cascadely DROP-CREATE changed entities and their dependencies',
    #                                   action='store_true',
    #                                   default=False)
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
    migrate_parser.set_defaults(func=migrate_command)
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
    diff_parser.set_defaults(func=diff_command)

    # status
    status_parser = subparsers.add_parser('status',
                                          help='Show unapplied migrations')
    status_parser.set_defaults(func=status_command)
    return _parser
