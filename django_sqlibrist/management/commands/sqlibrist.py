# -*- coding: utf8 -*-
from __future__ import absolute_import

import os
import sys
from contextlib import contextmanager

from django.core.management import BaseCommand
from django.db import connection

from django_sqlibrist.helpers import get_config
from django_sqlibrist.settings import SQLIBRIST_DIRECTORY
from sqlibrist.helpers import get_command_parser, SqlibristException, \
    handle_exception


@contextmanager
def chdir(target):
    current_dir = os.curdir
    os.chdir(target)
    yield
    os.chdir(current_dir)


class Command(BaseCommand):
    def add_arguments(self, parser):
        get_command_parser(parser)
        self.parser = parser

    def handle(self, *args, **options):
        _args = self.parser.parse_args(sys.argv[2:])

        config = get_config(_args)

        with chdir(SQLIBRIST_DIRECTORY):
            try:
                _args.func(_args, config, connection)
            except SqlibristException as e:
                handle_exception(e)
