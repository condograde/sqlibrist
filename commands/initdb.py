# -*- coding: utf8 -*-
from sys import stdout

from helpers import initdb as _initdb


def initdb(config, args):
    stdout.write(u'Creating db...\n')
    _initdb(config)
    stdout.write(u'Done.\n')
