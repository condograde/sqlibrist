# -*- coding: utf8 -*-
import glob
import hashlib
import os
import re
from json import loads, dumps
from sys import stdout

import psycopg2
import yaml
from yaml.scanner import ScannerError


class SqlibristException(Exception):
    pass


class CircularDependencyException(SqlibristException):
    pass


class UnknownDependencyException(SqlibristException):
    pass


class BadConfig(SqlibristException):
    pass


def get_config(args):
    try:
        with open(args.config_file) as config_file:
            configs = yaml.load(config_file.read())
    except IOError:
        raise BadConfig(u'No config file %s found!' % args.config_file)
    except ScannerError as e:
        raise BadConfig(u'Bad config file syntax')
    else:
        try:
            return configs[args.config]
        except KeyError:
            raise BadConfig(u'No config named %s found!' % args.config)


def get_connection(config):
    return psycopg2.connect(
            database=config.get('name'),
            user=config.get('user'),
            host=config.get('host'),
            password=config.get('password'),
            port=config.get('port'),
    )


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


def save_migration(schema, plan, suffix=''):
    migration_name = '%04.f%s' % (len(glob.glob('migrations/*')) + 1, suffix)
    dirname = os.path.join('migrations', migration_name)
    stdout.write(u'Creating new migration %s\n' % migration_name)
    os.mkdir(dirname)
    schema_filename = os.path.join(dirname, 'schema.json')
    with open(schema_filename, 'w') as f:
        f.write(dumps(schema, indent=2))

    up_filename = os.path.join(dirname, 'up.sql')
    with open(up_filename, 'w') as f:
        for item in plan:
            f.write('-- begin --\n')
            f.write('\n'.join(item.encode('utf8')).strip())
            f.write('\n')
            f.write('-- end --\n')
            f.write('\n')
            f.write('\n')


def mark_affected_items(schema, name):
    schema[name]['status'] = 'changed'
    for required in schema[name]['required']:
        mark_affected_items(schema, required)


def initdb(config):
    connection = get_connection(config)
    stdout.write(u'Creating schema and migrations log table...\n')
    with connection:
        with connection.cursor() as cursor:
            cursor.execute('''
            create schema if not exists sqlibrist;
            ''')

            cursor.execute('''
            create table if not exists sqlibrist.migrations (
            id SERIAL PRIMARY key,
            migration text,
            datetime TIMESTAMPTZ DEFAULT current_timestamp
            );
            ''')
    connection.close()


def handle_exception(e):
    if isinstance(e, CircularDependencyException):
        stdout.write(u'Circular dependency:\n')
        stdout.write(u'  %s' % u' >\n  '.join(e.message))
        stdout.write(u'\n')
    elif isinstance(e, UnknownDependencyException):
        stdout.write(u'Unknown dependency %s at %s\n' % e.message)
    elif isinstance(e, BadConfig):
        stdout.write(e.message + u'\n')
