from __future__ import print_function

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from product_details.management.commands.update_product_details import Command as PDCommand
from product_details.storage import PDDatabaseStorage, PDFileStorage

FIREFOX_VERSION_KEYS = (
    'FIREFOX_NIGHTLY',
    'FIREFOX_AURORA',
    'FIREFOX_ESR',
    'FIREFOX_ESR_NEXT',
    'LATEST_FIREFOX_DEVEL_VERSION',
    'LATEST_FIREFOX_RELEASED_DEVEL_VERSION',
    'LATEST_FIREFOX_VERSION',
)


class Command(BaseCommand):

    def __init__(self, stdout=None, stderr=None, no_color=False):
        self.file_storage = PDFileStorage(json_dir=settings.PROD_DETAILS_TEST_DIR)
        self.db_storage = PDDatabaseStorage()
        super(Command, self).__init__(stdout, stderr, no_color)

    def add_arguments(self, parser):
        parser.add_argument('-f', '--force', action='store_true', dest='force', default=False,
                            help=('Download product details even if they have '
                                  'not been updated since the last fetch.'))

        parser.add_argument('-q', '--quiet', action='store_true', dest='quiet', default=False,
                            help='If no error occurs, swallow all output.'),
        parser.add_argument('--database', default='default',
                            help=('Specifies the database to use, if using a db. '
                                  'Defaults to "default".')),

    def handle(self, *args, **options):
        if not settings.PROD_DETAILS_STORAGE.endswith('PDDatabaseStorage'):
            raise CommandError('Must be setup for database product-details storage to use this')

        self.update_file_data(options)
        try:
            self.validate_data()
        except Exception:
            raise CommandError('Product Details data is invalid')

        if not options['quiet']:
            print('Product Details data is valid')

        self.load_changes(options)

        if not options['quiet']:
            print('Product Details data update is complete')

    def load_changes(self, options):
        with transaction.atomic(using=options['database']):
            for filename in self.file_storage.all_json_files():
                fs_file_mtime = self.file_storage.last_modified_datetime(filename)
                db_file_mtime = self.db_storage.last_modified_datetime(filename)
                if options['force'] or not db_file_mtime or fs_file_mtime > db_file_mtime:
                    self.db_storage.update(filename,
                                           self.file_storage.content(filename),
                                           self.file_storage.last_modified(filename))
                    if not options['quiet']:
                        print('Updated ' + filename)

            self.db_storage.update('/', '', self.file_storage.last_modified('/'))
            self.db_storage.update('regions/', '', self.file_storage.last_modified('regions/'))

    def update_file_data(self, options):
        # json dir set in settings
        command = PDCommand()
        command._storage = self.file_storage
        command.is_db_storage = False
        command.handle(**options)

    def count_builds(self, version_key, min_builds=20):
        version = self.file_storage.data('firefox_versions.json')[version_key]
        if not version:
            if version_key == 'FIREFOX_ESR_NEXT':
                return
        builds = len([locale for locale, build in
                      self.file_storage.data('firefox_primary_builds.json').items()
                      if version in build])
        if builds < min_builds:
            raise ValueError('Too few builds for {}'.format(version_key))

    def validate_data(self):
        self.file_storage.clear_cache()
        for key in FIREFOX_VERSION_KEYS:
            self.count_builds(key)
