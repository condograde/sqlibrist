# -*- coding: utf8 -*-
from __future__ import print_function

from sqlibrist.helpers import get_last_schema, save_migration, \
    get_current_schema, compare_schemas, mark_affected_items


def makemigration(args, config, connection=None):
    empty = args.empty
    dry_run = args.dry_run
    migration_name = args.name

    current_schema = get_current_schema()
    execution_plan_up = []
    execution_plan_down = []

    if not empty:
        last_schema = get_last_schema() or {}

        added, removed, changed = compare_schemas(last_schema, current_schema)

        added_items = sorted([current_schema[name] for name in added],
                             key=lambda i: i['degree'])

        if added_items:
            print('Creating:')
            for item in added_items:
                print(' %s' % item['name'])

                execution_plan_up.append(item['up'])
                execution_plan_down.append(item['down'])

        for name in changed:
            current_schema[name]['status'] = 'changed'
        for name in changed:
            mark_affected_items(current_schema, name)

        changed_items = sorted([item
                                for item in current_schema.values()
                                if item.get('status') == 'changed'],
                               key=lambda i: i['degree'])

        if changed_items:
            print('Updating:')
            print(' dropping:')
            for item in reversed(changed_items):
                if item['down']:
                    print('  %s' % item['name'])

                if item['name'] in last_schema \
                        and last_schema[item['name']]['down']:
                    execution_plan_up.append(last_schema[item['name']]['down'])
                    execution_plan_down.append(last_schema[item['name']]['up'])
                elif item['name'] not in last_schema and item['name']['down']:
                    execution_plan_up.append(item['name']['down'])

            execution_plan_up.append(
                ['-- ==== Add your instruction here ===='])

            print(' creating:')
            for item in changed_items:
                if item['down']:
                    print('  %s' % item['name'])
                    execution_plan_up.append(item['up'])
                    execution_plan_down.append(item['down'])

        removed_items = sorted(
            [last_schema[name] for name in removed],
            key=lambda i: i['degree'],
            reverse=True)
        if removed_items:
            print('Deleting:')
            for item in removed_items:
                print(' %s' % item['name'])

                execution_plan_up.append(item['down'])
                execution_plan_down.append(last_schema[item['name']]['up'])

        default_suffix = 'auto'
    else:
        default_suffix = 'manual'

    suffix = ('-%s' % (migration_name or default_suffix))

    if not dry_run:
        save_migration(current_schema,
                       execution_plan_up,
                       reversed(execution_plan_down),
                       suffix)
