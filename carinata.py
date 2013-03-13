#!/usr/bin/env python
# coding: utf-8
"""
carinata: a (rough-scaled) python spec runner.
Copyright (C) 2013  Scott McGinnes <mcginness.s@gmail.com>

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


try:
    import cStringIO as StringIO
except ImportError:
    import StringIO


from .utils import identifier_safe, camelify, snakify, create_module_from_string


class Node(list):
    """Representation of a line in a spec file.

    Since spec files are structured hierarchically, we represent each line as a
    node in a tree structure. This is so that we can (eventually) flatten the
    tree and make a unittest.TestCase.

    """
    def __init__(self, words, indent=''):
        super(Node, self).__init__()
        self.words = words
        self.indent = indent
        self.parent = None
        self.processed = False

    def __repr__(self):
        return "<%s: '%s'>" % (self.__class__.__name__, self.words.strip())

    def add_leaf(self, obj):
        """Add a child node to this one"""
        self.append(obj)
        obj.parent = self

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
            if isinstance(node, Node) and not isinstance(node, leaf_class):
                for subnode in node.descendants(leaf_class):
                    yield subnode
            else:
                yield node

    def preparatories(self, prep_classes):
        """Get all the preparation-style nodes within this node.

        For example, returns all ‘before’ and ‘let’ blocks that are direct
        children of this node.

        """
        for node in self:
            for prep_class in prep_classes:
                if isinstance(node, prep_class):
                    yield node

    def leaves(self, leaf_class):
        """Get all children of type leaf_class within this node"""
        for node in self:
            if isinstance(node, leaf_class):
                yield node

    def stripped_lines(self, leaf_class):
        """Get all leaf_class children, stripping the common indentation"""
        first = True
        for leaf in self.leaves(leaf_class):
            if first:
                lstrip = re.search('[^\s]', leaf.words).start()
                first = False
            yield leaf.words[lstrip:]


class Describe(Node):
    """Representation of a ‘describe’ block"""
    pass


class Context(Node):
    """Representation of a ‘context’ block"""
    pass


class Before(Node):
    """Representation of a ‘before’ block"""
    pass


class Let(Node):
    """Representation of a ‘let’ block"""
    pass


class It(Node):
    """Representation of an ‘it’ block"""

    def siblings(self):
        """Get all the sibling ‘it’ blocks, including this one"""
        for node in self.parent:
            if isinstance(node, It):
                yield node

    def set_up(self, prep_classes):
        """Get all the preparation-style nodes that apply to this node.

        For example, this will search up the tree from this ‘it’ node, and
        yield all ‘before’ and ‘let’ nodes.

        """
        for parent in self.ancestors():
            for prep in parent.preparatories(prep_classes):
                yield prep


class Code(Node):
    """Representation of a line of code in a spec file"""
    def __init__(self, words, orig_file, orig_line):
        super(Code, self).__init__(words)
        self.orig_file = orig_file
        self.orig_line = orig_line

    def __str__(self):
        return ">>> %s" % self.words


class Test(Node):
    """Representation of an entire spec file.

    This is the main class that creates a unittest from a spec."""

    CLASS_LINE = "class %s(unittest.TestCase):\n"
    FUNC_LINE = "    def %s%s(self):\n"
    CODE_LINE = "        %s\n"
    CALL_BEFORE = "self._set_up_%s()"
    CALL_LET = "self.%s = self._set_up_%s()"

    def __init__(self, words, indent=''):
        super(Test, self).__init__(words, indent)
        self.class_names = []

    def _class_line(self, ancestors):
        """Concatentate ancestor names to form a unittest class name"""
        ancestor_names = [camelify(n.words) for n in ancestors]
        class_name = ''.join(reversed(ancestor_names))
        self.class_names.append(class_name)
        return self.CLASS_LINE % class_name

    def _func_line(self, func_name, is_test=True, is_set_up=False):
        """A function (‘test_*’ or ‘_set_up_*’) within a unittest class"""
        func_name = identifier_safe(func_name)
        if is_test:
            prefix = "test_"
        elif is_set_up:
            prefix = "_set_up_"
        else:
            prefix = ""
        return self.FUNC_LINE % (prefix, func_name)

    def _code_line(self, stripped_line):
        """Create an indented line of code from a pre-stripped line"""
        return self.CODE_LINE % stripped_line

    def _write_class(self, node, stream):
        """Write the class line to the stream"""
        stream.write(self._class_line(node.ancestors()))

    def _write_set_up(self, node, stream,
            prep_classes=None, leaf_class=Code):
        """Write the preparation-style functions to the stream"""
        # Store functions, so they can be called later
        set_up_funcs = []
        let_funcs = []

        # Define which nodes are used for preparation
        if prep_classes is None:
            prep_classes = [Before, Let]


        # Go though all set up functions above this node
        for i, set_up in enumerate(node.set_up(prep_classes)):
            func_name = snakify(set_up.words) + "_%d" % i

            # Decide whether this is a before block or a let assignment
            if isinstance(set_up, Before):
                func_list = set_up_funcs
            elif isinstance(set_up, Let):
                func_list = let_funcs
            func_list.append(func_name)

            # Put a private set up method on the test class
            stream.write(self._func_line(func_name, is_test=False,
                is_set_up=True))
            for code_line in set_up.stripped_lines(leaf_class):
                stream.write(self._code_line(code_line))
            stream.write("\n")

        # Write the main setUp() function, which calls the others
        stream.write(self._func_line("setUp", is_test=False))
        for func in set_up_funcs:
            code = self.CALL_BEFORE % func
            stream.write(self._code_line(code))
        for func in let_funcs:
            code = self.CALL_LET % (func, func)
            stream.write(self._code_line(code))
        stream.write("\n")

    def _write_tests(self, node, stream, leaf_class=Code):
        """Write the ‘test_*’ functions to the stream"""
        # Bundle up the it blocks
        for test in node.siblings():
            # Write the funtion line and the code
            stream.write(self._func_line(snakify(test.words)))
            for code_line in test.stripped_lines(leaf_class):
                stream.write(self._code_line(code_line))
            stream.write("\n")
        stream.write("\n")

    def read_spec_file(self, filepath):
        """Read a spec file into a tree with this node as root"""
        node = self

        with open(filepath) as file_to_read:
            contents = file_to_read.read()

        offset = 1
        for number, line in enumerate(contents.split("\n")):
            line_match = MATCH.match(line)
            if line_match:
                indent, name, words, rest = line_match.groups()
                parent = node
                node = CLASSES[name](words, indent)
                if len(indent) > len(parent.indent):
                    parent.add_leaf(node)
                else:
                    while (len(indent) <= len(parent.indent)
                            and parent.parent is not None):
                        parent = parent.parent
                    parent.add_leaf(node)
                if rest and not rest.isspace():
                    node.add_leaf(Code(rest, filepath, number + offset))

            elif not line or line.isspace():
                offset += 1
            else:
                node.add_leaf(Code(line, filepath, number + offset))

    def write_unittest_file(self, stream=sys.stdout, leaf_class=Code):
        """Write a unittest into the stream"""
        # Write top level code (usually just imports)
        stream.write("import unittest\n\n")
        for node in self.leaves(Code):
            stream.write(node.words + "\n")
        stream.write("\n\n")

        for node in self.descendants(leaf_class):
            if isinstance(node, It) and not node.parent.processed:
                self._write_class(node, stream)
                self._write_set_up(node, stream)
                self._write_tests(node, stream)

                node.parent.processed = True

        stream.write("__all__ = ['%s']\n\n" % ', '.join(self.class_names))
        stream.write("if __name__ == '__main__':\n    unittest.main()\n")


CLASSES = {
    'describe': Describe,
    'context': Context,
    'before': Before,
    'let': Let,
    'it': It,
}

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


def main():
    """Run a spec file as a unittest"""

    def carinata_files(directories):
        """Get a list of paths to spec files in directories"""
        for directory in directories:
            for root, _, filenames in os.walk(directory):
                for filename in filenames:
                    if os.path.splitext(filename)[1] == ".carinata":
                        yield os.path.join(root, filename)

    def create_test_modules(directories):
        """Create test modules from the spec files in directories"""
        test_modules = {}
        for filename in carinata_files(directories):
            test = Test('test')
            test.read_spec_file(filename)

            output = StringIO.StringIO()
            test.write_unittest_file(output)

            module_name = os.path.splitext(filename)[0]
            test_modules[module_name] = output
        return test_modules

    suite = unittest.TestSuite()
    directories = sys.argv[1:]
    if not directories:
        directories = ['./carinata']
    modules = create_test_modules(directories)
    for module_name, output in modules.iteritems():
        test = create_module_from_string(module_name, output.getvalue())
        module_suite = unittest.TestLoader().loadTestsFromModule(test)
        suite.addTest(module_suite)

    unittest.TextTestRunner().run(suite)


if __name__ == '__main__':
    main()
