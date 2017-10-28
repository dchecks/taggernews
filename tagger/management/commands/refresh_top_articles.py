from __future__ import print_function

import sys
import re

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone
from goose import Goose
from joblib import Parallel
from joblib import delayed

from tagger.models import Article, User

TOP_ARTICLES_URL = 'https://hacker-news.firebaseio.com/v0/topstories/.json'
LIMIT_TOP_RESULTS = 300
ITEM_URL = 'https://hacker-news.firebaseio.com/v0/item/%s.json'
THROTTLE = 5
THREAD_COUNT = 1  # Issues with this being >1 on OSX

URL_EXCLUSIONS = ["https://arxiv"]

emoji_regex = re.compile(
    u"(\ud83d[\ude00-\ude4f])|"  # emoticons
    u"(\ud83c[\udf00-\uffff])|"  # symbols & pictographs (1 of 2)
    u"(\ud83d[\u0000-\uddff])|"  # symbols & pictographs (2 of 2)
    u"(\ud83d[\ude80-\udeff])|"  # transport & map symbols
    u"(\ud83c[\udde0-\uddff])"  # flags (iOS)
    "+", flags=re.UNICODE)


class ArticleFetcher:

    def __init__(self):
        pass

    # Only want to update_rank when getting from the front 'ranked' page
    def fetch(self, article_ids, update_rank=False):
        """
            Given a list of article ids, collect them and their text in parallel
            @:param update_rank to be used with
            """
        ret_list = Parallel(n_jobs=THREAD_COUNT)(delayed(fetch_me)(aid) for aid in article_ids)

        return ret_list


def fetch_single(self, fetch_id):
    data = {fetch_id}
    articles, _, _, = self.fetch(data)
    if len(articles) is 1:
        return articles[0]
    else:
        return None


def goose_fetch(article_url):
    print("goosing " + article_url)
    goose = Goose()
    try:
        goosed_article = goose.extract(url=article_url)
        prediction_input = '%s|||\n\n%s' % (
            goosed_article.cleaned_text,
            goosed_article.meta_description,
        )
        state = 0
    except Exception as e:
        sys.stderr.write(str(e))
        state = 3
        prediction_input = None

    return prediction_input, state


def db_fetch(article_id):
    print("Fetching " + str(article_id))
    try:
        article = Article.objects.get(hn_id=article_id)
    except Article.DoesNotExist:
        article = None

    return article


def hn_fetch(article_id):
    print("Fetching from hn")
    article_info = requests.get(ITEM_URL % article_id).json()

    if article_info is None:
        print("HN id unknown ", article_id)
        article = Article.objects.create(
            hn_id=article_id,
            state=1,
            parsed=timezone.now()
        )
    else:
        url = article_info.get('url')
        if (not url) or url[:13] in URL_EXCLUSIONS:     # hack for goose as it doesnt like some unicode characters,
            print("No url for article ", article_id)
            state = 2
        else:
            state = 3

        submitter, created = User.objects.get_or_create(id=article_info.get('by'))

        article = Article.objects.create(
            hn_id=article_id,
            state=state,
            parsed=timezone.now(),
            title=article_info.get('title'),
            article_url=article_info.get('url'),
            score=article_info.get('score'),
            number_of_comments=article_info.get('descendants'),
            submitter=submitter,
            timestamp=article_info.get('time'),
        )
    return article


def fetch_me(article_id):
    # First, attempt to load straight from db
    article = db_fetch(article_id)

    if not article:
        # load the meta from HN
        article = hn_fetch(article_id)
        article.save()
    if not article.state or article.state is 3:
        # Get the article text
        try:
            (text, state) = goose_fetch(article.article_url)
            if state is 0:
                article.prediction_input = emoji_regex.sub(u'\uFFFD', text)  # strip emoji characters aka 4 byte chars
                article.state = state
            else:
                print("Failed to goose article: " + str(article.hn_id))
                article.state = state

            article.save()
        except Exception as e:
            print("Failed to save prediction input to db for " + str(article.hn_id))
            print(e)
            article.state = 5
            article.prediction_input = None
            article.save()

    return article


class Command(BaseCommand):
    help = 'Gets and ranks the homepage articles'

    def handle(self, *args, **options):
        top_article_ids = requests.get(TOP_ARTICLES_URL).json()[:LIMIT_TOP_RESULTS]

        articles = ArticleFetcher().fetch(top_article_ids)

        # Updates all to not ranked
        Article.objects.exclude(rank__isnull=True).update(rank=None)

        print('New order:')
        for i, article_id in enumerate(top_article_ids):
            arty = Article.objects.get(hn_id=article_id)
            arty.rank = i
            arty.save()
            print(str(i) + ": " + str(article_id))

        self.stdout.write(self.style.SUCCESS('Done. Fetched: %s' % (len(articles))))
