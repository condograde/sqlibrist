# -*- coding: utf8 -*-
from sys import stdout

from sqlibrist.helpers import initdb as _initdb, get_config


def initdb(args):
    config = get_config(args)
    stdout.write(u'Creating db...\n')
    _initdb(config)
    stdout.write(u'Done.\n')
