# Carinata #

## A (rough-scaled) python spec runner ##

Carinata is a python library which transforms spec files into unittest cases. It tries to be a bit like [RSpec](https://github.com/rspec/rspec-core), but for python

Spec files contain blocks called `describe`, `context`, `before`, `let` and `it`, which in turn contain pure python. Carinata uses these blocks to create `TestCase`s corresponding to each `it` block, with the setup from `before`s and `let`s.


## Usage ##

From a directory containing a bunch of spec files (extension `.carinata`)

```bash
$ carinata .
```

As a Django management command,

```bash
$ python manage.py spec someapp
```


## Examples ##

Suppose you need to test your simple class:

```python
class AwesomeClass(object):
    def __init__(self, operator, arg):
        self.operator = operator
        self.arg = arg

    def do_it(self):
        return operator(self.arg, 2)

    def get_it(self):
        return operator[self.arg]
```

You might test it like this:

```python
from unittest import TestCase
from mymodule import AwesomeClass

import operator

describe "AwesomeClass":
    before "each test":
        do_something_maybe_involving_a_database('?')
        
    let "get_awesome": lambda: AwesomeClass(self.operator, self.arg)

    context "with a multiplier and a 3":
        let "operator": operator.mul
        let "arg": 3
            
        it "returns a 6 when you do it":
            awesome = self.get_awesome()
            assert awesome.do_it() == 6

        it "returns a 9 when you bop it with a 3":
            awesome = self.get_awesome()
            assert awesome.bop_it(2) == 8

    context "with a dictionary and an 'a'":
        let "operator":
            return {'a': 1}
        let "arg": 'a'

        it "returns 1 when you get it":
            awesome = self.get_awesome()
            assert awesome.get_it() == 1
```
                
This will generate regular `unittest.TestCase`s from the `describe`, consisting of tests like
`test_returns_1_when_you_get_it()` in a class `TestAwesomeClassWithADictionaryAndAnA`.

The advantages with this approach include:

  * Self-documented tests, in plain english
  * Shared contexts and setup code, without copying and pasting
  * Your code is still just python

Some things to note:

  * The `let`s and `before`s are evaluated top-down. They are each put in the tests `setUp()`, and `let`s are assigned as attributes of `self`, where `before`s are just run. That is why we have a top level `lambda` which gets an awesome class: the arguments `self.operator` and `self.arg` are not defined until we hit the `context` blocks.
  * The `let` blocks can be defined without a `return`, but only if it is a single line (sort of as if they were `lambda`s). But `return` is required if they are more than one line, just like functions.
  * The test class that’s generated for multiple sibling `it` blocks is a *single* class, as you would expect.
  * The class to inherit test classes from is called `TestCase`. This needs to be imported somewhere before the first `describe` in each file. Remember, you can use any class for this, using an `import ... as TestCase`.


## Authors ##

Scott McGinness


## License (GPL version 3) ##

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

