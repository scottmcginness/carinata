# coding: utf-8
"""Create a test class from blocks"""
import re

from .utils import camelify, snakify
from .block import Block

_4 = " " * 4
_8 = _4 * 2

LSTRIP = re.compile(r'[^\s]')


class Creator(object):
    _filehash = "# sha1: {0}\n"
    _notice = """\
# This file was auto-generated by carinata
# It may be overwritten at any time, so please refer to the original:
# {0}
#
"""

    _klass = "class Test{0}(TestCase):\n"
    _part_set_up = _4 + "def _set_up_{0}(self):\n"
    _full_set_up = _4 + "def setUp(self):\n"
    _part_tear_down = _4 + "def _tear_down_{0}(self):\n"
    _full_tear_down = _4 + "def tearDown(self):\n"
    _call_set_up = _8 + "self._set_up_{0}()\n"
    _call_tear_down = _8 + "self._tear_down_{0}()\n"
    _assign = _8 + "self.{0} = self._set_up_{0}()\n"
    _test = _4 + "def test_{0}(self):\n"
    _code = "{0}{1}  # L:{2}\n"

    def __init__(self, stream):
        """Write each part of a test class into a stream from blocks.

        For each method, there is a corresponding format string (called _method)
        which should describe what is written.
        """
        self.stream = stream

    def filehash(self, hexdigest):
        self.stream.write(self._filehash.format(hexdigest))

    def notice(self, filepath):
        self.stream.write(self._notice.format(filepath))

    def klass(self, blocks):
        """A class definition line, with name based on names of blocks"""
        name = "".join(camelify(block.words) for block in blocks)
        self.stream.write(self._klass.format(name))

    def part_set_up(self, block):
        """Write a partial _set_up_*() defintion with body"""
        self.stream.write(self._part_set_up.format(block.words))
        self.code(block)

    def part_tear_down(self, block):
        """Write a partial _tear_down_*() defintion with body"""
        self.stream.write(self._part_tear_down.format(block.words))
        self.code(block)

    def full_set_up(self, blocks):
        """Write the setUp() definition with body"""
        self.stream.write(self._full_set_up)
        for block in blocks:
            if block.name == Block.before:
                self.call(block)
            elif block.name == Block.let:
                self.assign(block)
        self.line()

    def full_tear_down(self, blocks):
        """Write the tearDown() definition with body"""
        self.stream.write(self._full_tear_down)
        for block in blocks:
            self.call(block)
        self.line()

    def call(self, block):
        """Write a call to a partial _set_up_*() method"""
        if block.name == Block.before:
            call = self._call_set_up
        elif block.name == Block.after:
            call = self._call_tear_down
        self.stream.write(call.format(block.words))

    def assign(self, block):
        """Write a call to a _set_up_*(), and assign to self.*"""
        self.stream.write(self._assign.format(block.words))

    def test(self, block):
        """Write a test_*() method with body"""
        name = snakify(block.words)
        self.stream.write(self._test.format(name))
        self.code(block)

    def code(self, block, class_level=False):
        """Write the code contained in block, dedenting where necessary"""
        if not block.code:
            return
        start = LSTRIP.search(block.code[0][1]).start()
        indent = _4 if class_level else _8
        fmt = lambda l, n: self._code.format(indent, l[start:], n)
        lines = [fmt(line, lineno) for (lineno, line) in block.code]
        self.stream.writelines(lines)
        self.line()

    def line(self, content="", suffix=None):
        """Write a new line, with optional content"""
        if suffix is not None:
            line = self._code.format("", content, suffix)
        else:
            line = content + "\n"
        self.stream.write(line)

