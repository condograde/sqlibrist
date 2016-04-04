# -*- coding: utf8 -*-
from __future__ import print_function

import glob
import os

from sqlibrist.helpers import get_engine, ApplyMigrationFailed, \
    MigrationIrreversible


def unapplied_migrations(migration_list, applied_migrations):
    ml = [m.split('/')[-1] for m in migration_list]
    for migration in applied_migrations:
        try:
            ml.remove(migration[0])
        except ValueError:
            print('Miration "%s" is not in created '
                  'migration list, probably, this DB '
                  'is from another branch' % migration[0])
    return ml


def migrate(args, config, connection=None):
    fake = args.fake
    revert = args.revert
    till_migration_name = args.migration
    engine = get_engine(config, connection)

    applied_migrations = engine.get_applied_migrations()

    if applied_migrations and revert:
        last_applied_migration = applied_migrations[-1]
        try:
            with open(os.path.join('migrations',
                                   last_applied_migration,
                                   'down.sql')) as f:
                down = f.read()
        except IOError:
            raise MigrationIrreversible('Migration %s does not '
                                        'have down.sql - reverting '
                                        'impossible' % last_applied_migration)

        print('Un-Applying migration %s... ' % last_applied_migration, end='')
        if fake:
            print('(fake run) ', end='')
        try:
            engine.unapply_migration(last_applied_migration, down, fake)
        except ApplyMigrationFailed:
            print('Error, rolled back')
        else:
            print('done')
        return

    elif not revert:
        migration_list = unapplied_migrations(
            sorted(glob.glob('migrations/*')),
            applied_migrations)
    else:
        # no migrations at all
        migration_list = sorted(glob.glob('migrations/*'))

    for migration in migration_list:
        with open(os.path.join('migrations', migration, 'up.sql')) as f:
            up = f.read()

        migration_name = migration.split('/')[-1]
        print('Applying migration %s... ' % migration_name, end='')
        if fake:
            print('(fake run) ', end='')
        try:
            engine.apply_migration(migration_name, up, fake)
        except ApplyMigrationFailed:
            print('Error, rolled back')
            break
        else:
            print('done')
        if till_migration_name \
                and migration_name == till_migration_name:
            break
