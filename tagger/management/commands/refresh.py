from __future__ import print_function

import requests
from django.core.management.base import BaseCommand
import os

from django.core.wsgi import get_wsgi_application
from whitenoise.django import DjangoWhiteNoise

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tagger.settings")
    application = get_wsgi_application()
    application = DjangoWhiteNoise(application)

from tagger.models import Article
from tagger.article_fetcher import ArticleFetcher

TOP_ARTICLES_URL = 'https://hacker-news.firebaseio.com/v0/topstories/.json'
LIMIT_TOP_RESULTS = 300


def refresh_top():
    top_article_ids = requests.get(TOP_ARTICLES_URL).json()[:LIMIT_TOP_RESULTS]

    articles = ArticleFetcher().fetch(top_article_ids)

    # Updates all to not ranked
    Article.objects.exclude(rank__isnull=True).update(rank=None)

    print('New order:')
    for i, article_id in enumerate(top_article_ids):
        try:
            arty = Article.objects.get(hn_id=article_id)
            arty.rank = i
            arty.save()
            print(str(i) + ': ' + str(article_id))

            submitter = arty.submitter
            # if user on front page isn't tagged yet prioritise them
            if not submitter.tagged:
                submitter.priority = i
                submitter.save()

        except Article.DoesNotExist:
            print('Skipping ' + str(i) + ': ' + str(article_id))

    #self.stdout.write(self.style.SUCCESS('Done. Fetched: %s' % (len(articles))))

class Command(BaseCommand):
    help = 'Gets and ranks the homepage articles'

    def handle(self, *args, **options):
        refresh_top()

if __name__ == "__main__":
    refresh_top()
