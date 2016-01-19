# -*- coding: utf8 -*-
from sys import stdout

import os

DEFAULT_CONFIG_FILE = 'sqlibrist.yaml'
DEFAULT_CONFIG = """---
default:
  user: <username>
  name: <database_name>
  password: <password>
# host: 127.0.0.1
# port: 5432
"""


def init(args):
    stdout.write(u'Creating directories...\n')
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
    stdout.write(u'Done.\n')
