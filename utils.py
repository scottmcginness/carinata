# coding: utf-8
"""String utilities for creating unittest files from spec files"""
import imp


VALID_IDENTIFIER = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ" \
    "12345678990_"


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


def create_module_from_string(module_name, string):
    """Execute string as if it were a module, and return that module"""
    module = imp.new_module(module_name)
    exec string in module.__dict__
    return module


