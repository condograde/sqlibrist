# -*- coding: utf8 -*-
from __future__ import print_function

from sqlibrist.helpers import get_engine


def test_connection(args, config, connection=None):
    engine = get_engine(config, connection)

    db_connection = engine.get_connection()

    print('Connection OK')
    db_connection.close()
