# -*- coding: utf8 -*-
from __future__ import print_function
import os

from sqlibrist.helpers import get_engine, get_config


def status(config):
    """
    1. get applied migrations
    2. get all migrations
    3. check unapplied migrations
    """

    engine = get_engine(config)

    applied_migrations = {m[0] for m in engine.get_applied_migrations()}
    all_migrations = sorted(os.listdir('migrations/'))
    for i, migration in enumerate(all_migrations):
        if migration in applied_migrations:
            print('Migration %s - applied' % migration)
        else:
            print('Migration %s - NOT applied' % migration)


def status_command(args):
    return status(config=get_config(args))
