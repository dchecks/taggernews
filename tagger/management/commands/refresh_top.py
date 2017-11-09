from __future__ import print_function

import sys
import re

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone
from goose import Goose
from joblib import Parallel
from joblib import delayed

from tagger.models import Article, User, Item, ArticleText

TOP_ARTICLES_URL = 'https://hacker-news.firebaseio.com/v0/topstories/.json'
LIMIT_TOP_RESULTS = 300
ITEM_URL = 'https://hacker-news.firebaseio.com/v0/item/%s.json'
THROTTLE = 5
THREAD_COUNT = 1  # Issues with this being >1 on OSX

URL_EXCLUSIONS = ["https://arxiv", "http://arxiv"]

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
    def fetch(self, hn_ids):
        """
            Given a list of hn ids, collect them
            if the ids correspond to articles their text will also be fetched
        """
        ret_list = []
        for aid in hn_ids:
            ret_list.append(fetch_me(aid))

        return ret_list


def fetch_single(self, fetch_id):
    data = {fetch_id}
    articles, _, _, = self.fetch(data)
    if len(articles) is 1:
        return articles[0]
    else:
        return None


def goose_fetch(article_url):
    """Fetch the text from the given url"""
    print("goosing " + article_url)
    goose = Goose()
    try:
        goosed_article = goose.extract(url=article_url)
        text = '%s|||\n\n%s' % (
            goosed_article.cleaned_text,
            goosed_article.meta_description,
        )
        state = 0
    except Exception as e:
        sys.stderr.write(str(e))
        state = 3
        text = None

    return text, state


def db_fetch(hn_id):
    """Attempt to fetch from the db"""
    try:
        item = Article.objects.get(hn_id=hn_id)
        print("Fetching from db " + str(hn_id))
    except Article.DoesNotExist:
        item = None
        # TODO Remove this hackery when article subclasses item
        try:
            item = Item.objects.get(hn_id=hn_id)
        except Item.DoesNotExist:
            pass

    return item


def hn_fetch(article_id):
    """ Fetch the meta data from the hn api"""
    print("Fetching from hn " + str(article_id))
    try:
        article_info = requests.get(ITEM_URL % article_id).json()
    except Exception as e:
        print('Failed to get from hn api', e)
        article_info = None

    if article_info is None:
        print("HN id unknown ", article_id)
        return Article.objects.create(
            hn_id=article_id,
            state=1,
            parsed=timezone.now()
        )
    submitter_id = article_info.get('by')
    if submitter_id is None:
        submitter_id = 'deleted'
    submitter, created = User.objects.get_or_create(id=submitter_id)
    if article_info.get('type') != 'story':
        # Recurse to get the top_parent
        parent_id = article_info.get('parent')
        if parent_id is None:
            print('Failed to find the top parent for', parent_id)
            top_parent = None
            parent_item = None
        else:
            parent_item = fetch_me(parent_id)
            # When an article is returned, we know we've hit the top
            if isinstance(parent_item, Article):
                print('Found top parent', parent_id)
                top_parent = parent_item
                parent_item = None
            else:
                try:
                    if parent_item is None:
                        top_parent = None
                    elif parent_item.top_parent is None:
                        top_parent = None
                    else:
                        # the top_parent is at least 1 grandparent away, or not found
                        top_parent = parent_item.top_parent
                except Article.DoesNotExist as e:
                    top_parent = None


        item = Item(
            hn_id=article_id,
            submitter=submitter,
            type=article_info.get('type'),
            parent=parent_item,
            top_parent=top_parent
        )
    else:
        url = article_info.get('url')
        if (not url) or url.startswith(tuple(URL_EXCLUSIONS)):     # hack for goose as it doesnt like some unicode characters,
            print("No url for article ", article_id)
            state = 2
        else:
            state = 3
        item = Article.objects.create(
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

    item.save()
    return item


def fetch_me(hn_id):
    # First, attempt to load straight from db
    item = db_fetch(hn_id)

    if not item:
        # load the meta from HN
        item = hn_fetch(hn_id)

    if not isinstance(item, Article):
        return item
    else:
        article = item
        if article.state is None or article.state is 3:
            # Get the article text
            try:
                (text, state) = goose_fetch(article.article_url)
                if state is 0:
                    articletext = ArticleText( article=article,
                                                # strip emoji characters aka 4 byte chars
                                                text=emoji_regex.sub(u'\uFFFD', text),
                                                parsed=timezone.now())
                    article.articletext = articletext
                    article.state = state
                    articletext.save()
                else:
                    print("Failed to goose article: " + str(article.hn_id))
                    article.state = state

                article.save()
            except Exception as e:
                print("Failed to save prediction input to db for " + str(article.hn_id))
                print(e)
                article.state = 5
                article.articletext = None
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

        self.stdout.write(self.style.SUCCESS('Done. Fetched: %s' % (len(articles))))
