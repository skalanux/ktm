#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import ktm

version = ktm.__version__

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    print("You probably want to also tag the version now:")
    print("  git tag -a %s -m 'version %s'" % (version, version))
    print("  git push --tags")
    sys.exit()

readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

requirements = [
    # TODO: put package requirements here
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='ktm',
    version=version,
    description='Configurable notification daemon with queues and history display',
    long_description=readme + '\n\n' + history,
    author='Juan Manuel Schillaci',
    author_email='jmschillaci@gmail.com',
    url='https://github.com/skalanux/ktm',
    packages=[
        'ktm',
    ],
    package_dir={'ktm':
                 'ktm'},
    include_package_data=True,
    install_requires=requirements,
    license="GPLv3+",
    zip_safe=False,
    keywords='ktm',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
