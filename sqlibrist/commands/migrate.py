# -*- coding: utf8 -*-
import glob
import os
from sys import stdout

import psycopg2

from sqlibrist.helpers import get_connection, get_config


def unapplied_migrations(migration_list, last_migration):
    on = False
    for migration in migration_list:
        if migration.split('/')[-1] == last_migration:
            on = True
        elif on:
            yield migration


def migrate(args):
    config = get_config(args)
    connection = get_connection(config)

    with connection:
        with connection.cursor() as cursor:
            cursor.execute('''
            SELECT migration FROM sqlibrist.migrations
            ORDER BY datetime DESC
            LIMIT 1; ''')
            result = cursor.fetchone()

            if result:
                migration_list = unapplied_migrations(
                    sorted(glob.glob('migrations/*')),
                    result[0])
            else:
                # no migrations at all
                migration_list = sorted(glob.glob('migrations/*'))

            for migration in migration_list:
                with open(os.path.join(migration, 'up.sql')) as f:
                    up = f.read()

                try:
                    stdout.write(u'Applying migration %s... ' % migration)
                    if not args.fake:
                        cursor.execute(up)
                    else:
                        stdout.write(u'(fake run) ')
                except (psycopg2.OperationalError, psycopg2.ProgrammingError):
                    connection.rollback()
                    stdout.write(u'Error, rolled back\n')
                else:
                    stdout.write(u'done\n')
                    cursor.execute('''
                    INSERT INTO sqlibrist.migrations (migration) VALUES (%s);
                    ''', [migration.split('/')[-1]])
                    connection.commit()
