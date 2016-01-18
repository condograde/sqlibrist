# -*- coding: utf8 -*-
import psycopg2

from helpers import get_connection


def test_connection(config, args):
    try:
        connection = get_connection(config)
    except psycopg2.OperationalError as err:
        print('Error: %s' % err.message)
    else:
        print('Connection ok')
        connection.close()

