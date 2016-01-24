# -*- coding: utf8 -*-
from sys import stdout

from sqlibrist.helpers import get_last_schema, save_migration, \
    get_current_schema, compare_schemas, mark_affected_items


def makemigration(empty, dry_run, name):
    current_schema = get_current_schema()

    if not empty:
        last_schema = get_last_schema() or {}

        added, removed, changed = compare_schemas(last_schema, current_schema)

        execution_plan = []

        removed_items = sorted([last_schema[name] for name in removed],
                               key=lambda i: i['degree'],
                               reverse=True)
        if removed_items:
            stdout.write(u'Deleting:\n')
            for item in removed_items:
                print(u' %s' % item['name'])

            execution_plan.extend([item['down'] for item in removed_items])

        added_items = sorted([current_schema[name] for name in added],
                             key=lambda i: i['degree'])

        if added_items:
            stdout.write(u'Creating:\n')
            for item in added_items:
                stdout.write(u' %s\n' % item['name'])

            execution_plan.extend([item['up'] for item in added_items])

        for name in changed:
            current_schema[name]['status'] = 'changed'
        for name in changed:
            mark_affected_items(current_schema, name)

        changed_items = sorted([item
                                for item in current_schema.itervalues()
                                if item.get('status') == 'changed'],
                               key=lambda i: i['degree'])

        if changed_items:
            stdout.write(u'Updating:\n')
            stdout.write(u' dropping:\n')
            for item in reversed(changed_items):
                stdout.write(u'  %s\n' % item['name'])
            stdout.write(u' creating:\n')
            for item in changed_items:
                stdout.write(u'  %s\n' % item['name'])

            execution_plan.extend(
                    [item['down'] for item in reversed(changed_items)])
            execution_plan.extend([item['up'] for item in changed_items])

        suffix = ('-%s' % name) or '-auto'
    else:
        execution_plan = []
        suffix = ('-%s' % name) or '-manual'

    if not dry_run:
        save_migration(current_schema, execution_plan, suffix)


def makemigration_command(args):
    return makemigration(name=args.name, dry_run=args.dry_run, empty=args.empty)
