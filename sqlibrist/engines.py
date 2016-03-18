# -*- coding: utf8 -*-
from __future__ import absolute_import, print_function


class BaseEngine(object):
    def __init__(self, config):
        self.config = config

    def get_connection(self):
        raise NotImplementedError

    def create_migrations_table(self):
        raise NotImplementedError

    def get_applied_migrations(self):
        raise NotImplementedError

    def apply_migration(self, name, statements, fake=False):
        raise NotImplementedError

    def unapply_migration(self, name, statements, fake=False):
        raise NotImplementedError


class Postgresql(BaseEngine):
    def get_connection(self):
        import psycopg2
        return psycopg2.connect(
            database=self.config.get('name'),
            user=self.config.get('user'),
            host=self.config.get('host'),
            password=self.config.get('password'),
            port=self.config.get('port'),
        )

    def create_migrations_table(self):
        connection = self.get_connection()
        print('Creating schema and migrations log table...\n')
        with connection:
            with connection.cursor() as cursor:
                cursor.execute('CREATE SCHEMA IF NOT EXISTS sqlibrist;')

                cursor.execute('''
                CREATE TABLE IF NOT EXISTS sqlibrist.migrations (
                id SERIAL PRIMARY KEY,
                migration TEXT,
                datetime TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
                ''')
        connection.close()

    def get_applied_migrations(self):
        connection = self.get_connection()
        with connection:
            with connection.cursor() as cursor:
                cursor.execute('''
                SELECT migration FROM sqlibrist.migrations
                ORDER BY datetime; ''')
                return cursor.fetchall()

    def get_last_applied_migration(self):
        connection = self.get_connection()
        with connection:
            with connection.cursor() as cursor:
                cursor.execute('''
                SELECT migration FROM sqlibrist.migrations
                ORDER BY datetime DESC
                LIMIT 1; ''')
                result = cursor.fetchone()
                return result and result[0] or None

    def apply_migration(self, name, statements, fake=False):
        import psycopg2
        connection = self.get_connection()
        with connection:
            with connection.cursor() as cursor:
                try:
                    if not fake and statements.strip():
                        cursor.execute(statements)
                except (
                psycopg2.OperationalError, psycopg2.ProgrammingError) as e:
                    connection.rollback()
                    print(e.message)
                    from sqlibrist.helpers import ApplyMigrationFailed

                    raise ApplyMigrationFailed
                else:
                    cursor.execute('INSERT INTO sqlibrist.migrations '
                                   '(migration) VALUES (%s);',
                                   [name.split('/')[-1]])
                    connection.commit()

    def unapply_migration(self, name, statements, fake=False):
        import psycopg2
        connection = self.get_connection()
        with connection:
            with connection.cursor() as cursor:
                try:
                    if not fake:
                        cursor.execute(statements)
                except (
                psycopg2.OperationalError, psycopg2.ProgrammingError) as e:
                    connection.rollback()
                    print(e.message)
                    from sqlibrist.helpers import ApplyMigrationFailed

                    raise ApplyMigrationFailed
                else:
                    cursor.execute('DELETE FROM sqlibrist.migrations '
                                   'WHERE migration = (%s); ', [name])
                    connection.commit()
