# -*- coding: utf8 -*-
import os

from django.conf import settings

SQLIBRIST_DIRECTORY = getattr(settings,
                              'SQLIBRIST_DIRECTORY',
                              os.path.join(settings.BASE_DIR, 'sql'))
