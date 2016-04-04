# -*- coding: utf8 -*-
from __future__ import print_function

import os

DEFAULT_CONFIG_FILE = 'sqlibrist.yaml'
DEFAULT_CONFIG = """---
default:
  engine: pg
#  engine: mysql
  user: <username>
  name: <database_name>
  password: <password>
# host: 127.0.0.1
# port: 5432
"""


def init(args, config, connection=None):
    print('Creating directories...')
    dirlist = (
        'schema',
        'schema/tables',
        'schema/functions',
        'schema/views',
        'schema/triggers',
        'schema/indexes',
        'schema/types',
        'schema/constraints',
        'migrations'
    )

    for dirname in dirlist:
        if not os.path.isdir(dirname):
            os.mkdir(dirname)

    if not os.path.isfile(DEFAULT_CONFIG_FILE):
        with open(DEFAULT_CONFIG_FILE, 'w') as f:
            f.write(DEFAULT_CONFIG)
    print('Done.')
