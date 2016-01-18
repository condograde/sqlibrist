# -*- coding: utf8 -*-
import glob
import hashlib
import os
import re
from json import loads, dumps
from sys import stdout

import psycopg2


class CircularDependencyException(Exception):
    pass


class UnknownDependencyException(Exception):
    pass


def get_connection(config):
    return psycopg2.connect(database=config.get('name'),
                            user=config.get('user'))


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


def test_for_circular_dependencies(schema, name, metadata, stack=()):
    if name in stack:
        raise CircularDependencyException(stack + (name,))
    for requires in metadata['requires']:
        test_for_circular_dependencies(schema,
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
        test_for_circular_dependencies(schema, name, metadata)
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
    stdout.write(u'Creating new migration %s...\n' % migration_name)
    os.mkdir(dirname)
    with open(os.path.join(dirname, 'schema.json'), 'w') as f:
        f.write(dumps(schema, indent=2))

    with open(os.path.join(dirname, 'up.sql'), 'w') as f:
        for item in plan:
            f.write('-- started --\n')
            f.write('\n'.join(item).strip())
            f.write('\n')
            f.write('-- ended --\n')
            f.write('\n')
            f.write('\n')

    # with open(os.path.join(dirname, 'down.sql'), 'w') as f:
    #     for item in reversed(plan):
    #         f.write(u'-- "%s" started --\n' % item)
    #         f.write(u'\n'.join(schema[item]['down']))
    #         f.write(u'\n')
    #         f.write(u'-- "%s" ended --\n' % item)
    #         f.write(u'\n')


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
