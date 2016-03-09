# -*- coding: utf8 -*-
from __future__ import print_function

from sqlibrist.helpers import get_config, get_engine


def initdb(config):
    engine = get_engine(config)

    print('Creating db...')
    engine.create_migrations_table()
    print('Done.')


def initdb_command(args):
    initdb(get_config(args))
