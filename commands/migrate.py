# -*- coding: utf8 -*-
import glob
import os

import psycopg2

from helpers import get_connection


def left_migrations(migration_list, last_migration):
    on = False
    for migration in migration_list:
        if migration.split('/')[-1] == last_migration:
            on = True
        elif on:
            yield migration


def migrate(config, args):
    connection = get_connection(config)

    with connection:
        with connection.cursor() as cursor:
            cursor.execute('''
            select migration from sqitchpy.migrations
            order by datetime desc
            LIMIT 1; ''')
            result = cursor.fetchone()

            if result:
                migration_list = left_migrations(sorted(glob.glob('migrations/*')),
                                                 result[0])
            else:
                # no migrations at all
                migration_list = sorted(glob.glob('migrations/*'))

            for migration in migration_list:
                with open(os.path.join(migration, 'up.sql')) as f:
                    up = f.read()
                print(up)
                try:
                    cursor.execute(up)
                except (psycopg2.OperationalError, psycopg2.ProgrammingError):
                    connection.rollback()
                    print('Error, rolled back')
                else:
                    print('All ok')
                    cursor.execute('''
                    insert into sqitchpy.migrations (migration) VALUES (%s)
                    ''', [migration.split('/')[-1]])
                    connection.commit()
