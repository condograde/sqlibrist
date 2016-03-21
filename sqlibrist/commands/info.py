# -*- coding: utf8 -*-
from __future__ import print_function


def info(args, config):
    from sqlibrist import VERSION
    print('Version: %s' % VERSION)
    print(config)
