#!/usr/bin/env python
# coding: utf-8
"""
carinata: a (rough-scaled) python spec generator.
Copyright (C) 2013  Scott McGinness <mcginness.s@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
import os
import re
import sys
import tempfile
import unittest

from . import utils
from .block import Block
from .creator import Creator


MATCH = re.compile(r'''
    ^(?P<indent>\s*)   # whitespace indent
    (?P<name>describe|context|before|after|let|it)  # block name
    \s"                                             # space, then open quote
    (?P<words>[^"]*?)                               # words of description
    "*                                              # close quote
    (?P<args>\s?\([^\)]*\))?                        # optional function args
    :                                               # then end with colon
    \s?(?P<rest>.*)$                                # code at end
''', re.VERBOSE)


class TestGenerator(object):
    def __init__(self, filepath, stream=sys.stdout):
        """Read the contents of a spec file and setup the generator"""
        with open(filepath) as file_to_read:
            contents = file_to_read.read()
        self.filehash = utils.get_hash_from_contents(contents)
        self.filepath = os.path.abspath(filepath)
        self.creator = Creator(stream)
        self.lines = contents.split("\n")
        self.blocks = [Block("", Block.test, "", 0)]
        self.deferred_its = []
        self.deferred_decorators = []

    def process(self):
        """Do the main processing of the spec file"""
        self.creator.filehash(self.filehash)
        self.creator.notice(self.filepath)
        for lineno, line in enumerate(self.lines):
            line_match = MATCH.match(line)
            if line_match:
                self.process_line_match(lineno+1, line_match)
            elif not line or line.isspace() or line.lstrip().startswith('#'):
                self.deferred_decorators = []
            elif line.lstrip().startswith('@'):
                self.deferred_decorators.append((lineno+1, line.lstrip()))
            else:
                self.process_code(lineno+1, line)

        # Process any leftover deferred it blocks. There should be one
        # since we usually defer the final it block in any given tree.
        self.process_its()

    def process_line_match(self, lineno, line_match):
        """If the line matched a block, process that block"""
        indent, name, words, args, rest = line_match.groups()

        if name != Block.it and self.deferred_its:
            self.process_its(args)

        block = Block(indent, name, words, lineno, rest)

        if len(self.blocks) != 1 and block.indent <= self.blocks[-1].indent:
            self.blocks = [b for b in self.blocks
                           if b.is_applicable(block.indent)]
        self.blocks.append(block)

        if block.name == Block.it:
            if args is not None:
                block.args = args
            self.defer_it()
        elif self.deferred_decorators:
            block.decorators = self.deferred_decorators[:]
            self.deferred_decorators = []

    def process_code(self, lineno, line):
        """Write code lines into stream or append to block"""
        stripped = line.strip()
        if len(self.blocks) == 1:
            # At the top level, so write immediately
            self.creator.line(line, lineno)
        else:
            # Inside a block, so defer it
            self.blocks[-1].code.append((lineno, line))
        self.deferred_decorators = []  # don't accumulate actual decorators

    def defer_it(self):
        """Put an ‘it’ block on a list to be bundled into a test class"""
        self.blocks[-1].decorators = self.deferred_decorators[:]
        self.deferred_decorators = []
        self.deferred_its.append(self.blocks[-1])

    def process_its(self, args=None):
        """Process the ‘it’ blocks given the context in the spec file"""
        structures, setups, teardowns = self.split_block_types()

        # This should be the last it block in the list, and we were passed args
        if args is not None and len(deferred_its == 1):
            block.args = args

        self.creator.klass(structures)
        for block in structures:
            self.creator.code(block, class_level=True)
        for setup in setups:
            self.creator.part_set_up(setup)
        for teardown in teardowns:
            self.creator.part_tear_down(teardown)
        if setups:
            self.creator.full_set_up(setups)
        if teardowns:
            self.creator.full_tear_down(teardowns)

        for it in self.deferred_its:
            self.creator.test(it)
        self.creator.line()
        self.deferred_its = []

    def split_block_types(self):
        """Split the list of blocks into structural and setup code"""
        structures, setups, teardowns = [], [], []
        for block in self.blocks:
            if block.name in [Block.describe, Block.context]:
                structures.append(block)
            elif block.name == Block.let:
                if block in setups:
                    setups.remove(block)
                setups.append(block)
            elif block.name == Block.before:
                setups.append(block)
            elif block.name == Block.after:
                teardowns.append(block)
        return structures, setups, teardowns


class SuiteGenerator(object):
    """Generate python test files or a unittest.TestSuite"""
    SUFFIX = ".carinata"
    TEMPDIR = os.path.join(tempfile.gettempdir(), "carinata")

    def __init__(self, directories, output_dir=None, force_generation=False, clean=False):
        self.directories = directories
        self.output_dir = output_dir
        self.force_generation = force_generation
        self.clean = clean

    def spec_files(self):
        """Get a list of paths to spec files in directories"""
        for directory in self.directories:
            for root, _, filenames in os.walk(directory):
                for filename in filenames:
                    if os.path.splitext(filename)[1] == self.SUFFIX:
                        yield directory, os.path.join(root, filename)

    def create_test_files(self):
        """Create python test files from the spec files"""
        filepaths = []
        for indir, infile in self.spec_files():
            if self.clean:
                outdir, outfile = self._get_output(indir, infile)
                try:
                    os.remove(outfile)
                except OSError:
                    pass
                continue
            try:
                with self.output_file(indir, infile) as outfile:
                    test = TestGenerator(infile, outfile)
                    test.process()
                path = outfile.name
            except utils.FileHashMatch as hash_match:
                path = hash_match.filename
            filepaths.append(path)

        return filepaths

    def create_test_suite(self):
        """Create a unittest suite from the spec files"""
        suite, loader = unittest.TestSuite(), unittest.TestLoader()
        filepaths = self.create_test_files()
        for filepath in filepaths:
            test = utils.create_module_from_file(filepath)
            suite.addTest(loader.loadTestsFromModule(test))
        return suite

    def _get_output(self, indir, infile):
        outdir = self.output_dir if self.output_dir else self.TEMPDIR

        outfile = infile.replace(self.SUFFIX, ".py")
        outfile = os.path.join(outdir,
                               os.path.relpath(outfile, indir))
        outdir = os.path.dirname(outfile)

        return outdir, outfile

    def output_file(self, indir, infile):
        """Get a file-like object for output.

        If an output_dir was given, put the file in there. Otherwise, put it
        in the temporary directory.
        """
        outdir, outfile = self._get_output(indir, infile)
        if not os.path.exists(outdir):
            os.makedirs(outdir)

        # Check the hash of the output file and raise exception if it matches
        # that of the input file
        if not self.force_generation:
            utils.check_file_hash(infile, outfile)

        return open(outfile, 'w')


def main(directories, output_dir, generate, force, clean):
    """Generate and run spec files.

    Collect spec files from directories and process them into a test suite.
    If output_dir is given, put the test files into it, preserving directory
    structure from each parent directory. If generate is given, only generate
    the files, otherwise run with the usual unittest text runner.
    """
    generator = SuiteGenerator(directories, output_dir, force, clean)

    if generate:
        generator.create_test_files()
    else:
        suite = generator.create_test_suite()
        if not clean:
            unittest.TextTestRunner().run(suite)


def parse_args():
    """Define and parse command line arguments"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("directories", action="append",
                        help="The list of directories in which to search for"
                        " spec files (always recursive)")

    parser.add_argument("-o", "--output-dir", dest="output_dir",
                        help="The directory in which to create output test"
                        " files (Created in a temporary directory if this"
                        " argument is not given)")

    parser.add_argument("-g", "--generate", action="store_true", default=False,
                        help="Only generate test files, do not run them"
                        " (False by default, so tests will run if this"
                        " argument is not given)")

    parser.add_argument("-f", "--force", action="store_true", default=False,
                        help="Generate test files regardless of whether"
                        " original files have changed or not (False by"
                        " default, so only changed tests are generated)")

    parser.add_argument("-c", "--clean", action="store_true", default=False,
                        help="Clean up files instead of generating them")

    return parser.parse_args()


def main_cmdline():
    """Run carinata as main package, taking arguments from sys.argv"""
    args = parse_args()
    main(args.directories, args.output_dir, args.generate, args.force,
         args.clean)


if __name__ == '__main__':
    main_cmdline()
