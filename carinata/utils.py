# coding: utf-8
"""String utilities for creating unittest files from spec files"""
import os
import sys
import uuid


VALID_IDENTIFIER = ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    "12345678990_")


def _camel_safe(name):
    """Remove all non-identifier chars and underscores from name"""
    return identifier_safe(name).replace("_", "")


def identifier_safe(name):
    """Remove all non-identifier chars from name"""
    return "".join(char for char in name if char in VALID_IDENTIFIER)


def camelify(words):
    """Return a camel-cased version of words"""
    return "".join(_camel_safe(w) for w in words.title() if not w.isspace())


def snakify(words):
    """Return a snake-cased version of words"""
    return "_".join(identifier_safe(w) for w in words.lower().split())


def create_module_from_file(filepath):
    """Execute string as if it were a module, and return that module"""
    name = os.path.splitext(os.path.basename(filepath))[0]
    directory = os.path.dirname(filepath)
    if directory not in sys.path:
        sys.path.insert(0, directory)
    return __import__(name)


def uuid_hex(length=6):
    return "_x" + uuid.uuid4().hex[:length]

