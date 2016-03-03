# -*- coding: utf8 -*-
from sys import stdout

from sqlibrist.helpers import get_last_schema, save_migration, \
    get_current_schema, compare_schemas, mark_affected_items


def makemigration(empty, dry_run, migration_name):
    current_schema = get_current_schema()
    execution_plan_up = []
    execution_plan_down = []

    if not empty:
        last_schema = get_last_schema() or {}

        added, removed, changed = compare_schemas(last_schema, current_schema)

        removed_items = sorted([last_schema[name] for name in removed],
                               key=lambda i: i['degree'],
                               reverse=True)
        if removed_items:
            stdout.write(u'Deleting:\n')
            for item in removed_items:
                stdout.write(u' %s\n' % item['name'])

                execution_plan_up.append(item['down'])
                execution_plan_down.append(last_schema[item['name']]['up'])

        added_items = sorted([current_schema[name] for name in added],
                             key=lambda i: i['degree'])

        if added_items:
            stdout.write(u'Creating:\n')
            for item in added_items:
                stdout.write(u' %s\n' % item['name'])

                execution_plan_up.append(item['up'])
                execution_plan_down.append(item['down'])

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
                if item['down']:
                    stdout.write(u'  %s\n' % item['name'])

                if item['name'] in last_schema \
                        and last_schema[item['name']]['down']:
                    execution_plan_up.append(last_schema[item['name']]['down'])
                    execution_plan_down.append(last_schema[item['name']]['up'])
                elif item['name'] not in last_schema and item['name']['down']:
                    execution_plan_up.append(item['name']['down'])

            execution_plan_up.append(
                [u'-- ==== Add your instruction here ===='])

            stdout.write(u' creating:\n')
            for item in changed_items:
                if item['down']:
                    stdout.write(u'  %s\n' % item['name'])
                    execution_plan_up.append(item['up'])
                    execution_plan_down.append(item['down'])

        default_suffix = 'auto'
    else:
        default_suffix = 'manual'

    suffix = ('-%s' % (migration_name or default_suffix))

    if not dry_run:
        save_migration(current_schema,
                       execution_plan_up,
                       reversed(execution_plan_down),
                       suffix)


def makemigration_command(args):
    return makemigration(migration_name=args.name,
                         dry_run=args.dry_run,
                         empty=args.empty)
