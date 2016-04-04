# -*- coding: utf8 -*-
from __future__ import absolute_import, print_function


class BaseEngine(object):
    def __init__(self, config, connection=None):
        self.config = config
        self.connection = connection

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
        if self.connection is None:
            import psycopg2
            self.connection = psycopg2.connect(
                database=self.config.get('name'),
                user=self.config.get('user'),
                host=self.config.get('host'),
                password=self.config.get('password'),
                port=self.config.get('port'),
            )
        return self.connection

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
                        psycopg2.OperationalError,
                        psycopg2.ProgrammingError) as e:
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
                        psycopg2.OperationalError,
                        psycopg2.ProgrammingError) as e:
                    connection.rollback()
                    print(e.message)
                    from sqlibrist.helpers import ApplyMigrationFailed

                    raise ApplyMigrationFailed
                else:
                    cursor.execute('DELETE FROM sqlibrist.migrations '
                                   'WHERE migration = (%s); ', [name])
                    connection.commit()


class MySQL(BaseEngine):
    def get_connection(self):
        if self.connection is None:
            import MySQLdb
            self.connection = MySQLdb.connect(
                db=self.config.get('name'),
                user=self.config.get('user'),
                host=self.config.get('host', '127.0.0.1'),
                passwd=self.config.get('password'),
                port=self.config.get('port'),
            )
        return self.connection

    def create_migrations_table(self):
        connection = self.get_connection()
        cursor = connection.cursor()
        print('Creating migrations log table...\n')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sqlibrist_migrations (
            id SERIAL PRIMARY KEY,
            migration TEXT,
            `datetime` TIMESTAMP
           );
        ''')

    def get_applied_migrations(self):
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute('''
            SELECT migration FROM sqlibrist_migrations
            ORDER BY `datetime`; ''')
        return cursor.fetchall()

    def get_last_applied_migration(self):
        connection = self.get_connection()
        cursor = connection.cursor()

        cursor.execute('''
            SELECT migration FROM sqlibrist_migrations
            ORDER BY `datetime` DESC
            LIMIT 1; ''')
        result = cursor.fetchone()
        return result and result[0] or None

    def apply_migration(self, name, statements, fake=False):
        import MySQLdb
        connection = self.get_connection()
        cursor = connection.cursor()

        try:
            if not fake and statements.strip():
                cursor.execute(statements)
        except (MySQLdb.OperationalError, MySQLdb.ProgrammingError) as e:
            print('\n'.join(map(str, e.args)))
            from sqlibrist.helpers import ApplyMigrationFailed

            raise ApplyMigrationFailed
        else:
            cursor.execute('INSERT INTO sqlibrist_migrations '
                           '(migration) VALUES (%s);',
                           [name.split('/')[-1]])

    def unapply_migration(self, name, statements, fake=False):
        import MySQLdb
        connection = self.get_connection()
        cursor = connection.cursor()

        try:
            if not fake:
                cursor.execute(statements)
        except (MySQLdb.OperationalError, MySQLdb.ProgrammingError) as e:
            print('\n'.join(map(str, e.args)))
            from sqlibrist.helpers import ApplyMigrationFailed

            raise ApplyMigrationFailed
        else:
            cursor.execute('DELETE FROM sqlibrist_migrations '
                           'WHERE migration = (%s); ', [name])
