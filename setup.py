# -*- coding: utf8 -*-
import sqlibrist
import os
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='sqlibrist',
    version=sqlibrist.VERSION,
    packages=['sqlibrist', 'django_sqlibrist'],
    include_package_data=True,
    license='MIT License',
    description='Simple tool for managing DB structure, automating patch '
                'creation for DB structure migration.',
    long_description=README,
    url='https://github.com/condograde/sqlibrist',
    author='Serj Zavadsky',
    author_email='fevral13@gmail.com',
    install_requires=['PyYAML'],
    classifiers=[
        'Environment :: Web Environment',
        'Environment :: Console',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Database',
        'Topic :: Database :: Database Engines/Servers',
        'Topic :: Utilities',
    ],
    keywords='sqlibrist, db structure, sql, schema migration',
    entry_points={
        'console_scripts': [
            'sqlibrist=sqlibrist:main'
        ]
    }
)
