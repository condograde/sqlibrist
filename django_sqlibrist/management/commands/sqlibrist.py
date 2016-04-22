# -*- coding: utf8 -*-
from __future__ import absolute_import

import os
from contextlib import contextmanager

from django.core.management import BaseCommand
from django.db import connection

from django_sqlibrist.helpers import get_config, Args
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

    def handle(self, *args, **options):
        config = get_config()

        with chdir(SQLIBRIST_DIRECTORY):
            try:
                options['func'](Args(options), config, connection)
            except SqlibristException as e:
                handle_exception(e)
