import carinata
import os
import sys
from optparse import make_option

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    args = '<app>'
    option_list = BaseCommand.option_list + (
        make_option('--testclass', default="django.test.TestCase"),
    )

    def handle(self, *apps, **options):
        if not apps:
            sys.stderr.write("""\
Please specify at least one app to run specs on.
""")
            sys.exit(1)
        test_class = options.get('testclass')
        for app in apps:
            directories = [os.path.join(app, "spec")]
            carinata.main(directories, test_class, os.path.join(app, "tests"))
        call_command('test', app)
