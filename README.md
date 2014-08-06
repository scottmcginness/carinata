# Carinata #

## A (rough-scaled) python spec runner ##

Carinata is a python library which transforms spec files into unittest cases.
It tries to be a bit like [RSpec](https://github.com/rspec/rspec-core), but
for python

Spec files contain blocks called `describe`, `context`, `before`, `after`,
`let` and `it`, which in turn contain pure python. Carinata uses these blocks
to create a `TestCase` corresponding to each `it` block, with the setup from
`before` and `let` and the teardown from `after`.


## Installation ##

As usual (you’re using a [virtualenv](http://www.virtualenv.org/en/latest/)
[right](http://virtualenvwrapper.readthedocs.org/en/latest/)?), either do
```bash
$ pip install carinata
```
or grab the [latest code]() from GitHub and install that
```bash
$ git clone https://github.com/scottmcginness/carinata.git
$ cd carinata
$ python setup.py install
```

## Usage ##

From a directory containing a bunch of spec files (extension `.carinata`)

```bash
$ carinata .
```

As a Django management command,

```bash
$ ./manage.py spec someapp
```

See `carinata --help` for a few more options.


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
                
This will generate regular `unittest.TestCase`s from the `describe`,
consisting of tests like `test_returns_1_when_you_get_it()` in a class
called `TestAwesomeClassWithADictionaryAndAnA`.

The advantages with this approach include:

  * Self-documented tests, in plain english
  * Shared contexts and setup code, without copying and pasting
  * Your code is still just python

Some things to note:

  * The `before`, `after` and `let` blocks are evaluated top-down. They are
    each put in the test’s `setUp()` or `tearDown()`, and `let` blocks are
    assigned as attributes of `self`. Each `before` and `after` may be thought
    of as just a partial setup or teardown.
  * That is why we have a top level `lambda` which gets an awesome class: the
    arguments `self.operator` and `self.arg` are not defined until we hit the
    `context` blocks.
  * The `let` blocks can be defined without a `return`, but only if it is a
    single line (sort of as if they were a `lambda`). But `return` is required
    if they are more than one line, just like functions.
  * The test class that’s generated for multiple sibling `it` blocks is a
    *single* class, as you would expect.
  * The class to inherit test classes from is called `TestCase`. This needs to
    be imported somewhere before the first `describe` in each file. Remember,
    you can use any class for this, using an `import ... as TestCase`.
  * You can throw in arbitrary code (so long as it’s indented correctly) under
    `describe` and `context` and it will be picked up as class code. This may be
    useful if you require class attributes, like `fixtures = ['myfix']`.


## Django ##

All the above comes in useful when you want to test your Django app. The
following uses [factory_boy](https://github.com/dnerdy/factory_boy) to help
generate models and [python-faker](https://github.com/redneckbeard/python-faker)
to generate test data (you don’t have to, of course, but they do make your
life easier).

Given the following model, and factory to describe it:

```python
# models.py
from django.db import models
from django.contrib.auth.models import User

class BlogPost(models.Model):
    user = models.ForeignKey(User)
    slug = models.CharField(max_length=60)
    title = models.CharField(max_length=60)
    body = models.TextField(null=False, blank=False)

    def save(self, *args, **kwargs):
        if not self.slug.endswith("-suffix"):
            self.slug += "-suffix"
        super(BlogPost, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return "/posts/{0}".format(self.pk)


# factories.py
import factory
from faker.lorem import words, paragraphs
from myapp.models import *

class UserFactory(factory.DjangoModelFactory):
    FACTORY_FOR = User
    # Some definitions for User model
    # ...

class BlogPostFactory(factory.DjangoModelFactory):
    FACTORY_FOR = BlogPost
    user = factory.SubFactory(User)
    slug = factory.LazyAttribute(lambda b: "-".join(words(4)))
    title = factory.LazyAttribute(lambda b: " ".join(words(4)).title())
    body = factory.LazyAttribute(lambda b: "\n".join(paragraphs(5)))
```

you might test it like this:

```python
from myapp.spec.factories import *
from django.test import TestCase

describe "BlogPost":
    let "user": UserFactory()

    context "with valid attributes":
        let "blog_post": BlogPost.build()

        it "saves a suffix on the slug":
            assert not self.blog_post.slug.endswith("-suffix")
            self.blog_post.save()
            assert self.blog_post.slug.endswith("-suffix")

        it "has URL /posts/pk":
            self.blog_post.save()
            pk = self.blog_post.pk
            expected = "/posts/{0}".format(pk)
            actual = self.blog_post.get_absolute_url()  
            assert actual == expected

    context "with a blank body":
        let "blog_post": BlogPost.build(body="")

        it "fails to save":
            try:
                self.blog_post.save()
            except:
                pass
            else:
                assert False, "Blog post saved without a body"
```

With this short toy example (admittedly with some factory boilerplate)
we can read and write the tests easily. I recommened using
[sure](https://github.com/gabrielfalcao/sure) if you want those
asserts to be less painful. Then you’ll get something even more RSpec‐like.

In the end, carinata will generate a file `myapp/tests/models.py`, something like:

```python
from myapp.spec.factories import *
from django.test import TestCase

class TestBlogPostWithValidAttributes(TestCase):
    def _set_up_user(self):
        return UserFactory()

    def _set_up_blog_post(self):
        return BlogPost.build(user=self.user)

    def setUp(self):
        self.user = self._set_up_user()
        self.blog_post = self._set_up_blog_post()

    def test_saves_a_suffix_on_the_slug(self):
        assert not self.blog_post.slug.endswith("-suffix")
        self.blog_post.save()
        assert self.blog_post.slug.endswith("-suffix")

    def test_has_url_posts_pk(self):
        self.blog_post.save()
        pk = self.blog_post.pk
        expected = "/posts/{0}".format(pk)
        actual = self.blog_post.get_absolute_url()  
        assert actual == expected
        
class TestBlogPostWithABlankBody(TestCase):
    def _set_up_user(self):
        return UserFactory()

    def _set_up_blog_post(self):
        return BlogPost.build(body="", user=self.user)

    def setUp(self):
        self.user = self._set_up_user()
        self.blog_post = self._set_up_blog_post()

    def test_fails_to_save(self):
        try:
            self.blog_post.save()
        except:
            pass
        else:
            assert False, "Blog post saved without a body"
```

Comparing the two, there is a little less setup to do in our spec file.
All that’s needed is to run `./manage.py spec myapp` and you should get
the standard tests generated and run.

If you want to be slightly fancier about it,
[django-nose](https://github.com/jbalogh/django-nose) with the
[pinocchio](http://darcs.idyll.org/~t/projects/pinocchio/doc/#spec-generate-test-description-from-test-class-method-names)
spec plugin are also recommended. Once you’ve `pip install`ed those, your
`settings.py` should contain:

```python

INSTALLED_APPS = (
    'myapp',
    # ... the usual stuff ...
    'carinata',
    'django_nose',
    'pinocchio',
) 

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

NOSE_ARGS = ('--with-spec', '--spec-color')
NOSE_PLUGINS = ('pinocchio.spec.Spec',)
```

Running `./manage.py spec myapp`, and you’ll get lovely colored readable test output.


## Decorators ##

You may apply decorators to `describe` and `context` blocks (where they will be applied
to the generated class) and `it` blocks (where they will be applied to the test method.

For example:

```python

@my_class_helper
describe "MyClass":

    @my_inner_class_helper
    context "with some condition":

        @test_method_decorator
        it "can be tested":
            assert True

    context "without that condition":

        @test_method_decorator
        it "can also be tested":
            assert True

```

which generates two classes with their respective decorators:

```python

@my_class_helper
@my_inner_class_helper
class MyClassWithSomeCondition(TestCase):
    @test_method_decorator
    def test_can_be_tested(self):
        assert True

@my_class_helper
class MyClassWithoutThatCondition(TestCase):
    @test_method_decorator
    def test_can_also_be_tested(self):
        assert True

```

This comes in useful when using features of [mock](http://www.voidspace.org.uk/python/mock/),
such as `patch`ing. Since this can also change the function signature, you may specify
a custom set of arguments for your `it` lines, like this:

```python

import mock

describe "Mocking":
    @mock.patch('my_module.log')
    it "can be useful" (self, log):
        assert not log.call_args_list

```


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

