#!/usr/bin/env python
import os
from distutils.core import setup

def get_packages():
    packages = []
    for root, _, filenames in os.walk('carinata'):
        if '__init__.py' in filenames:
            packages.append(".".join(os.path.split(root)).strip("."))
    return packages

_long_description = """\
Carinata is a command line tool which transforms spec files into unittest cases.
It tries to be a bit like RSpec, but for python. It includes a management
command for Django.

Spec files contain blocks called ``describe``, ``context``, ``before``, ``after``,
``let`` and ``it``, which in turn contain pure python. Carinata uses these blocks
to create a ``TestCase`` corresponding to each ``it`` block, with the setup from
``before`` and ``let`` and the teardown from ``after``.

See the `project homepage`_ on GitHub for more information, but here is an example::

    describe "My Awesome class":
        context "with the number 42":
            let "awesome": Awesome(42)

            it "jumps for joy":
                assert self.awesome.jumps_for_joy()

        context "with a string":
            let "awesome": Awesome('wow!')

            it "says it":
                assert self.awesome.say() == "Awesome says 'wow!'"

.. _project homepage: https://github.com/scottmcginness/carinata
"""


setup(name='carinata',
      version='0.10.4',
      description='A rough-scaled python spec generator',
      long_description=_long_description,
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

