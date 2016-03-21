# -*- coding: utf8 -*-
from __future__ import print_function

from sqlibrist.helpers import get_engine


def test_connection(args, config):
    engine = get_engine(config)

    connection = engine.get_connection()

    print('Connection OK')
    connection.close()
