#!/usr/bin/env python

from distutils.core import setup

setup(name='carinata',
      version='0.1.2',
      description='A rough-scaled python spec runner',
      author='Scott McGinness',
      author_email='mcginness.s@gmail.com',
      url='https://github.com/scottmcginness/carinata',
      packages=['carinata'],
      install_requires=['astor >= 0.2.1']
     )
