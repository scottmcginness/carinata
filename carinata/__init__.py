#!/usr/bin/env python
# coding: utf-8
"""
carinata: a (rough-scaled) python spec runner.
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
import unittest
from astor import codegen


try:
    import cStringIO as StringIO
except ImportError:
    import StringIO


from carinata.utils import create_module_from_string
from carinata import creator


class InvalidLeafError(Exception):
    """Error caused when node is given a bad child.

    See VALID_CHILDREN for allowable trees.
    """
    pass


def _valid_children():
    """Create the VALID_CHILREN dict describing allowed trees"""
    valid_children = {
        'test': 'describe code',
        'describe': 'describe context before let it',
        'context': 'context before let it',
        'before': 'code',
        'let': 'code',
        'it': 'code',
        'code': ''
    }
    for parent, children in valid_children.iteritems():
        valid_children[parent] = children.split()
    return valid_children


VALID_CHILDREN = _valid_children()


class Node(list):
    """Representation of a line in a spec file.

    Since spec files are structured hierarchically, we represent each line as a
    node in a tree structure. This is so that we can (eventually) flatten the
    tree and make a unittest.TestCase.

    """
    def __init__(self, words, indent='', name=None):
        super(Node, self).__init__()
        self.name = name
        self.words = words
        self.indent = indent
        self.parent = None
        self.processed = False
        self.valid_leaves = VALID_CHILDREN[self.name] if self.name else None
        self.code_lines = []

    def __repr__(self):
        return "<%s: '%s'>" % (self.__class__.__name__, self.words.strip())

    def add_leaf(self, obj):
        """Add a child node to this one"""
        if self.valid_leaves is None or obj.name in self.valid_leaves:
            self.append(obj)
            obj.parent = self
        else:
            msg = "cannot add %s leaf to a %s node" % (obj.name, self.name)
            raise InvalidLeafError(msg)

    def add_code(self, code_line):
        """Add some code to this node"""
        if 'code' in self.valid_leaves:
            self.code_lines.append(code_line)

    def code(self):
        """Newline separated code lines"""
        return "\n".join(c.words for c in self.code_lines)

    def dedented_code(self):
        """Get all leaf_class children, stripping the common indentation"""
        if not self.code_lines:
            return ""

        lstrip = re.search(r'[^\s]', self.code_lines[0].words).start()
        return "\n".join(line.words[lstrip:] for line in self.code_lines)

    def ancestors(self):
        """Get the parents up to the root node"""
        parent = self.parent
        while parent is not None:
            yield parent
            parent = parent.parent

    def pretty(self, stream=sys.stdout):
        """Print this node and its children"""
        stream.write(self.indent + repr(self) + "\n")
        for obj in self:
            obj.pretty()

    def descendants(self, leaf_class):
        """Generate this node and all subnodes.

        Walks depth-first through all descendants of this node (including this
        node). Stops yielding subnodes if this node is a type of leaf_class.

        """
        yield self
        for node in self:
            if node.name is None or node.name != leaf_class:
                for subnode in node.descendants(leaf_class):
                    yield subnode
            else:
                yield node

    def preparatories(self):
        """Get all the preparation-style nodes within this node.

        For example, returns all ‘before’ and ‘let’ blocks that are direct
        children of this node.

        """
        for node in self:
            if node.name in ['before', 'let']:
                yield node

    def leaves(self, leaf_class):
        """Get all children of type leaf_class within this node"""
        for node in self:
            if node.name == leaf_class:
                yield node

    def siblings(self):
        """Get all the sibling ‘it’ blocks, including this one"""
        for node in self.parent:
            if node.name == 'it':
                yield node

    def setup(self):
        """Get all the preparation-style nodes that apply to this node.

        For example, this will search up the tree from this ‘it’ node, and
        yield all ‘before’ and ‘let’ nodes.

        """
        for parent in self.ancestors():
            for prep in parent.preparatories():
                yield prep



class TestGenerator(object):
    """Representation of an entire spec file.

    This is the main class that creates a unittest from a spec."""

    def __init__(self):
        self.node = Node("Test", name="test")

    def read_spec_file(self, filepath):
        """Read a spec file into a tree with this node as root"""
        node = self.node

        with open(filepath) as file_to_read:
            contents = file_to_read.read()

        for line in contents.split("\n"):
            line_match = MATCH.match(line)
            if line_match:
                indent, name, words, rest = line_match.groups()
                parent = node
                node = Node(words, indent, name=name)
                if len(indent) > len(parent.indent):
                    parent.add_leaf(node)
                else:
                    while (len(indent) <= len(parent.indent)
                            and parent.parent is not None):
                        parent = parent.parent
                    parent.add_leaf(node)
                if rest and not rest.isspace():
                    node.add_code(Node(rest, filepath, name='code'))
            elif not line or line.isspace():
                continue
            else:
                node.add_code(Node(line, filepath, name='code'))

    def create_ast(self, test_module, test_class):
        """Create AST for this unittest module"""
        module = creator.module(self.node, test_module, test_class)
        for node in self.node.descendants('code'):
            if node.name == 'it' and not node.parent.processed:
                klass = creator.klass(node, test_class)
                module.body.append(klass)
                node.parent.processed = True
        main_runner = creator.main_runner(test_module)
        module.body.append(main_runner)
        return module

class SuiteGenerator(object):
    """Generate a unittest.TestSuite from files in directories"""

    def __init__(self, directories, test_class, output_dir=None):
        self.directories = directories
        test_class_parts = test_class.split('.')
        self.test_class = test_class_parts[-1]
        self.test_module = '.'.join(test_class.split('.')[:-1])
        self.output_dir = output_dir

    def carinata_files(self):
        """Get a list of paths to spec files in directories"""
        for directory in self.directories:
            for root, _, filenames in os.walk(directory):
                for filename in filenames:
                    if os.path.splitext(filename)[1] == ".carinata":
                        yield directory, os.path.join(root, filename)

    def create_test_modules(self):
        """Create test modules from the spec files in directories"""
        test_modules = {}
        for directory, filename in self.carinata_files():
            test = TestGenerator()
            test.read_spec_file(filename)

            if self.output_dir:
                filename = os.path.relpath(filename, directory)
                output_path = os.path.join(self.output_dir, filename.replace("carinata", "py"))
                output = open(output_path, 'w')
            else:
                output = StringIO.StringIO()

            test_ast = test.create_ast(self.test_module, self.test_class)
            code = codegen.to_source(test_ast)
            output.write(code)

            module_name = os.path.splitext(os.path.basename(filename))[0]
            test_modules[module_name] = filename if self.output_dir else output
        return test_modules

    def create_suite(self):
        """Main function to create a test suite"""
        suite = unittest.TestSuite()
        modules = self.create_test_modules()
        for module_name, output in modules.iteritems():
            test = create_module_from_string(module_name, output.getvalue())
            module_suite = unittest.TestLoader().loadTestsFromModule(test)
            suite.addTest(module_suite)
        return suite


MATCH = re.compile(r'''
    ^(?P<indent>\s*)                          # whitespace indent
    (?P<name>describe|context|before|let|it)  # block name
    [\s\(]                                    # space or open paren
    "?                                        # optionally quote
    (?P<words>[^"]*?)                         # words of description
    "?                                        # optionally unquote
    \)?                                       # optionally close paren
    :                                         # colon ends statement
    \s?(?P<rest>.*)$                          # code at end
''', re.VERBOSE)


def main(directories=None, test_class="unittest.TestCase", output_dir=None):
    """Run a spec file as a unittest"""
    if not directories:
        directories = ['.']

    gen = SuiteGenerator(directories, test_class, output_dir)

    if output_dir is None:
        suite = gen.create_suite()
        unittest.TextTestRunner().run(suite)
    else:
        gen.create_test_modules()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("directories", action="append")
    parser.add_argument("--test-class")
    args = parser.parse_args()
    main(args.directories, args.test_class)
