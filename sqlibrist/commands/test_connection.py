# -*- coding: utf8 -*-
from __future__ import print_function

from sqlibrist.helpers import get_engine, get_config


def test_connection(config):
    engine = get_engine(config)

    connection = engine.get_connection()

    print('Connection OK')
    connection.close()


def test_connection_command(args):
    return test_connection(config=get_config(args))
