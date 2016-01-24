# -*- coding: utf8 -*-
import glob
import os
from sys import stdout

from sqlibrist.helpers import get_engine, get_config, ApplyMigrationFailed


def unapplied_migrations(migration_list, last_migration):
    on = False
    for migration in migration_list:
        if migration.split('/')[-1] == last_migration:
            on = True
        elif on:
            yield migration


def migrate(config, fake, till_migration_name):
    engine = get_engine(config)

    last_applied_migration = engine.get_last_applied_migration()

    if last_applied_migration:
        migration_list = unapplied_migrations(
            sorted(glob.glob('migrations/*')),
            last_applied_migration)
    else:
        # no migrations at all
        migration_list = sorted(glob.glob('migrations/*'))

    for migration in migration_list:
        with open(os.path.join(migration, 'up.sql')) as f:
            up = f.read()

        migration_name = migration.split('/')[-1]
        stdout.write(u'Applying migration %s... ' % migration_name)
        if fake:
            stdout.write(u'(fake run) ')
        try:
            engine.apply_migration(migration_name, up, fake)
        except ApplyMigrationFailed:
            stdout.write(u'Error, rolled back\n')
        else:
            stdout.write(u'done\n')
        if migration_name.startswith(till_migration_name):
            break


def migrate_command(args):
    return migrate(config=get_config(args),
                   fake=args.fake,
                   till_migration_name=args.migration)
