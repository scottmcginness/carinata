#!/usr/bin/env python
import os
from distutils.core import setup

def get_packages():
    packages = []
    for root, _, filenames in os.walk('carinata'):
        if '__init__.py' in filenames:
            packages.append(".".join(os.path.split(root)).strip("."))
    return packages

setup(name='carinata',
      version='0.3.0',
      description='A rough-scaled python spec runner',
      author='Scott McGinness',
      author_email='mcginness.s@gmail.com',
      url='https://github.com/scottmcginness/carinata',
      packages=get_packages(),
      install_requires=['astor >= 0.2.1']
     )
