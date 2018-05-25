from __future__ import print_function

import traceback
import requests
import os
import logging

from django.core.management.base import BaseCommand

from django.core.wsgi import get_wsgi_application
from whitenoise.django import DjangoWhiteNoise
if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tagger.settings")
    application = get_wsgi_application()
    application = DjangoWhiteNoise(application)

from tagger.models import Article
from tagger.article_fetcher import ArticleFetcher
from tagger.comment_fetcher import CommentFetcher

TOP_ARTICLES_URL = 'https://hacker-news.firebaseio.com/v0/topstories/.json'
ITEM_URL = 'https://hacker-news.firebaseio.com/v0/item/%s.json'
LIMIT_TOP_RESULTS = 300

arty = ArticleFetcher()
commy = CommentFetcher()

def update_rank(top_article_ids):
    logging.info('Updating rank...')
    # Updates all to not ranked
    Article.objects.exclude(rank__isnull=True).update(rank=None)
    logging.info('New order:')
    for i, article_id in enumerate(top_article_ids):
        try:
            arty = Article.objects.get(hn_id=article_id)
            arty.rank = i
            arty.save()
            logging.info(str(i) + ': ' + str(article_id))

            submitter = arty.submitter
            # if user on front page isn't tagged yet prioritise them
            if submitter.state not in [10, 99]:
                submitter.priority = i
                submitter.save()

        except Article.DoesNotExist:
            logging.info('Skipping ' + str(i) + ': ' + str(article_id))


def collect_comments(article_dict):
    logging.info('Collecting kids...')
    for key in article_dict.keys():
        arty.fetch(article_dict[key])


def update_scores(top_article_ids):
    logging.info('Updating scores')
    for article_id in top_article_ids:
        try:
            article_info = requests.get(ITEM_URL % article_id).json()
            article = Article.objects.get(hn_id=article_id)
            article.score = article_info.get('score')
            article.number_of_comments = article_info.get('descendants')
            article.save()
        except Exception as e:
            logging.info('Failed to save scores for article ' + str(article_id))
            traceback.print_exc(e)


def refresh_top():
    top_article_ids = requests.get(TOP_ARTICLES_URL).json()[:LIMIT_TOP_RESULTS]

    arty.fetch(top_article_ids)
    logging.info('Fetched: %s' % (len(top_article_ids)))

    update_rank(top_article_ids)
    update_scores(top_article_ids)

    logging.info('Done')


class Command(BaseCommand):
    help = 'Gets and ranks the homepage articles'

    def handle(self, *args, **options):
        refresh_top()

if __name__ == "__main__":
    refresh_top()
