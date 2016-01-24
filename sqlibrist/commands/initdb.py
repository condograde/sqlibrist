# -*- coding: utf8 -*-
from sys import stdout

from sqlibrist.helpers import get_config, get_engine


def initdb(config):
    engine = get_engine(config)

    stdout.write(u'Creating db...\n')
    engine.create_migrations_table()
    stdout.write(u'Done.\n')


def initdb_command(args):
    initdb(get_config(args))
