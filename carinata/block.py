# coding: utf-8
"""A simple block class to wrap spec blocks"""
from . import utils


class Block(object):
    """Represent a block structure by indent, name, description and code"""
    test = 'test'
    describe = 'describe'
    context = 'context'
    before = 'before'
    let = 'let'
    it = 'it'

    valid_children = {
        test: [describe],
        describe: [describe, context, before, let, it],
        context: [context, before, let, it],
        before: [],
        let: [],
        it: [],
    }

    def __init__(self, indent, name, words, rest=None):
        self.indent = len(indent)
        self.name = name
        self.words = words
        self.code = []
        if rest:
            if self.name == self.let and not rest.startswith('return'):
                rest = "return (%s)" % rest
            self.code.append(rest)
        if self.name == self.before:
            self.words += utils.uuid_hex()

    def __repr__(self):
        return "<%s: %s>" % (self.name, self.words)

    def is_applicable(self, indent):
        """Determine whether this block applies at the given indent"""
        if self.name == self.test:
            return True
        elif self.indent > indent:
            return False
        elif self.indent == indent:
            return self.name not in [self.describe, self.context, self.it]
        return True
