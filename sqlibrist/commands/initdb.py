# -*- coding: utf8 -*-
from __future__ import print_function

from sqlibrist.helpers import get_engine


def initdb(args, config):
    engine = get_engine(config)

    print('Creating db...')
    engine.create_migrations_table()
    print('Done.')


