# -*- coding: utf8 -*-
from sys import stdout

from helpers import get_last_schema, save_migration, get_current_schema, \
    compare_schemas, CircularDependencyException, UnknownDependencyException, \
    mark_affected_items


def makemigration(config, args):
    # collect schema
    try:
        current_schema = get_current_schema()
    except CircularDependencyException as e:
        stdout.write(u'Circular dependency:\n')
        stdout.write(u'  %s' % u' >\n  '.join(e.message))
        stdout.write(u'\n')
        return
    except UnknownDependencyException as e:
        stdout.write(u'Unknown dependency %s at %s\n' % e.message)
        return

    if not args.empty:
        last_schema = get_last_schema() or {}

        added, removed, changed = compare_schemas(last_schema, current_schema)

        execution_plan = []

        removed_items = sorted([last_schema[name] for name in removed],
                               key=lambda i: i['degree'],
                               reverse=True)
        print(u'Deleting:')
        for item in removed_items:
            print(u' %s' % item['name'])

        execution_plan.extend([item['down'] for item in removed_items])

        added_items = sorted([current_schema[name] for name in added],
                             key=lambda i: i['degree'])

        print(u'Creating:')
        for item in added_items:
            print(u' %s' % item['name'])

        execution_plan.extend([item['up'] for item in added_items])

        for name in changed:
            current_schema[name]['status'] = 'changed'
        for name in changed:
            mark_affected_items(current_schema, name)

        changed_items = sorted([item
                                for item in current_schema.itervalues()
                                if item.get('status') == 'changed'],
                               key=lambda i: i['degree'])

        print(u'Updating:')
        print(u' dropping:')
        for item in reversed(changed_items):
            print(u'  %s' % item['name'])
        print(u' creating:')
        for item in changed_items:
            print(u'  %s' % item['name'])

        execution_plan.extend([item['down'] for item in reversed(changed_items)])
        execution_plan.extend([item['up'] for item in changed_items])

        suffix = '-auto'
    else:
        execution_plan = []
        suffix = '-manual'

    if not args.dry_run:
        save_migration(current_schema, execution_plan, suffix)