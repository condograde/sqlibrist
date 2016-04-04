# -*- coding: utf8 -*-
from __future__ import print_function

from sqlibrist.helpers import get_engine


def initdb(args, config, connection=None):
    engine = get_engine(config, connection)

    print('Creating db...')
    engine.create_migrations_table()
    print('Done.')


