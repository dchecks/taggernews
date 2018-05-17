from django.core.management.base import BaseCommand

from tagger.tag_article import tag


class Command(BaseCommand):
    help = 'tags articles'

    def handle(self, *args, **options):
        tag()
