# coding: utf-8
"""String utilities for creating unittest files from spec files"""
import hashlib
import os
import sys
import uuid


VALID_IDENTIFIER = ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    "12345678990_")


class FileHashMatch(Exception):
    """The persisted file has a hash, and it matched the current file hash"""
    pass


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


def get_hash_from_contents(contents):
    return hashlib.sha1(contents).hexdigest()


def get_hash_from_filename(filename, block=2**12):
    sha1 = hashlib.sha1()
    with open(filename) as f:
        while True:
            data = f.read(block)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()


def get_hash_from_first_line(filename):
    with open(filename, 'r') as f:
        hash_line = f.readline()
    try:
        return hash_line.split(':')[1].strip()
    except IndexError:
        return ""


def check_file_hash(input_filename, output_path):
    current_hash = get_hash_from_filename(input_filename)
    if os.path.exists(output_path):
        old_hash = get_hash_from_first_line(output_path)
        if current_hash == old_hash:
            raise FileHashMatch(current_hash)
