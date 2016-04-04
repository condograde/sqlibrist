# -*- coding: utf8 -*-
from __future__ import print_function

import difflib

from sqlibrist.helpers import get_last_schema, get_current_schema, \
    compare_schemas


def diff(args, config, connection=None):
    verbose = args.verbose
    last_schema = get_last_schema()

    current_schema = get_current_schema()

    added, removed, changed = compare_schemas(last_schema, current_schema)

    if any((added, removed, changed)):
        if added:
            print('New items:')
            for item in added:
                print('  %s' % item)

        if removed:
            print('Removed items:')
            for item in removed:
                print('  %s' % item)

        if changed:
            print('Changed items:')
            for item in changed:
                print('  %s' % item)
                if verbose:
                    _diff = difflib.unified_diff(last_schema[item]['up'],
                                                 current_schema[item]['up'])
                    print('\n'.join(_diff))

    else:
        print('No changes')
