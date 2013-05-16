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
      version='0.10.0',
      description='A rough-scaled python spec runner',
      author='Scott McGinness',
      author_email='mcginness.s@gmail.com',
      url='https://github.com/scottmcginness/carinata',
      download_url='https://github.com/scottmcginness/carinata/archive/master.zip',
      packages=get_packages(),
      scripts=['scripts/carinata'],
      keywords=['testing', 'test', 'rspec'],
      classifiers=[
          "Development Status :: 3 - Alpha",
          "Environment :: Console",
          "Framework :: Django",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
          "Natural Language :: English",
          "Operating System :: OS Independent",
          "Topic :: Software Development :: Code Generators",
          "Topic :: Software Development :: Quality Assurance",
          "Topic :: Software Development :: Testing",
      ]
)

