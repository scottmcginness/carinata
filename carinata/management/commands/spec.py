import carinata
import os
import sys
from optparse import make_option

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    args = '<directory directory ...>'
    option_list = BaseCommand.option_list + (
        make_option('--app'),
        make_option('--testclass', default="django.test.TestCase"),
    )

    def handle(self, *directories, **options):
        app = options.get('app')
        if app is None:
            sys.stderr.write("""\
Please specify which app needs its specs generated (use --app=<appname>)
""")
            sys.exit(1)
        test_class = options.get('testclass')
        if not directories:
            directories = [os.path.join(app, "spec")]
        carinata.main(directories, test_class, os.path.join(app, "tests"))
        call_command('test', app)
