import carinata
import os
import sys
from optparse import make_option

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    args = '<app>'
    option_list = BaseCommand.option_list + (
        make_option('-g', '--generate', action="store_true", default=False,
                    help="Only generate test files, do not run them"
                    " (False by default, so tests will run if this"
                    " argument is not given)"),
        make_option("-f", "--force", action="store_true", default=False,
                    help="Generate test files regardless of whether"
                    " original files have changed or not (False by"
                    " default, so only changed tests are generated)"),
    )

    def handle(self, *apps, **options):
        if not apps:
            sys.stderr.write("""\
Please specify at least one app to run specs on.
""")
            sys.exit(1)

        generate = options.pop('generate')
        force = options.pop('force')
        for app in apps:
            directories = [os.path.join(app, "spec")]
            carinata.main(directories, os.path.join(app, "tests"), generate=True, force=force)
        if not generate:
            call_command('test', app)
