#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# From https://github.com/ionelmc/python-nameless

from __future__ import absolute_import
from __future__ import print_function

import io
from glob import glob
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import splitext

from setuptools import find_packages
from setuptools import setup


def read(*names, **kwargs):
    return io.open(
        join(dirname(__file__), *names),
        encoding=kwargs.get('encoding', 'utf8')
    ).read()


setup(
    name='natnet',
    version='0.1.0',
    author='Matthew Edwards',
    author_email='matthew@matthewedwards.co.nz',
    url='git@github.com:mje-nz/python-natnet',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'attrs>=17.2'
    ],
    extras_require={
        ':python_version<"3.5"': ['typing'],
        ':python_version<"3.4"': ['enum34']
    }
)
