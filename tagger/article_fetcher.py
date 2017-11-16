import re
import sys
import traceback

import requests
import time
from django.db import IntegrityError
from django.db import OperationalError
from goose import Goose
from django.utils import timezone
from models import Article, User, Item, ArticleText

ITEM_URL = 'https://hacker-news.firebaseio.com/v0/item/%s.json'
URL_EXCLUSIONS = ["https://arxiv", "http://arxiv"]

emoji_regex = re.compile(
    u"(\ud83d[\ude00-\ude4f])|"  # emoticons
    u"(\ud83c[\udf00-\uffff])|"  # symbols & pictographs (1 of 2)
    u"(\ud83d[\u0000-\uddff])|"  # symbols & pictographs (2 of 2)
    u"(\ud83d[\ude80-\udeff])|"  # transport & map symbols
    u"(\ud83c[\udde0-\uddff])"  # flags (iOS)
    "+", flags=re.UNICODE)
# Failed on \\xF0\\x9F\\x8C\\x89


class ArticleFetcher:
    STAT_TOTAL_REQUESTED = 0
    STAT_INTEGRITY_ERROR = 0

    STAT_ITEM_FROM_DB = 0
    STAT_ITEM_FROM_HN = 0
    STAT_ITEM_NO_TOP_PARENT = 0
    STAT_ITEM_CREATED = 0

    STAT_ARTICLE_FROM_DB = 0
    STAT_ARTICLE_FROM_HN = 0
    STAT_ARTICLE_NO_URL = 0
    STAT_ARTICLE_CREATED = 0

    STAT_HN_REQUEST = 0
    STAT_HN_BACKOFF = 0
    STAT_HN_UNKNOWN = 0

    STAT_USER_CREATED = 0

    STAT_GOOSE_FETCH = 0
    STAT_GOOSE_FAILURE = 0

    def __init__(self):
        pass

    def print_stats(self):
        print('------STATS------\n'
              'STAT_TOTAL_REQUESTED = %s\n'
              'STAT_HN_REQUEST = %s\n'
              'STAT_ARTICLE_FROM_DB = %s\n'
              'STAT_ARTICLE_FROM_HN = %s\n'
              'STAT_ITEM_FROM_DB = %s\n'
              'STAT_ITEM_FROM_HN = %s\n'
              'STAT_ARTICLE_CREATED = %s\n'
              'STAT_ITEM_CREATED = %s\n'
              'STAT_ITEM_NO_TOP_PARENT = %s\n'
              'STAT_INTEGRITY_ERROR = %s\n'
              'STAT_ARTICLE_NO_URL = %s\n'
              'STAT_HN_BACKOFF = %s\n'
              'STAT_HN_UNKNOWN = %s\n'
              'STAT_USER_CREATED = %s\n'
              'STAT_GOOSE_FETCH = %s\n'
              'STAT_GOOSE_FAILURE = %s\n\n' % (self.STAT_TOTAL_REQUESTED,
                                           self.STAT_HN_REQUEST,
                                           self.STAT_ARTICLE_FROM_DB,
                                           self.STAT_ARTICLE_FROM_HN,
                                           self.STAT_ITEM_FROM_DB,
                                           self.STAT_ITEM_FROM_HN,
                                           self.STAT_ARTICLE_CREATED,
                                           self.STAT_ITEM_CREATED,
                                           self.STAT_ITEM_NO_TOP_PARENT,
                                           self.STAT_INTEGRITY_ERROR,
                                           self.STAT_ARTICLE_NO_URL,
                                           self.STAT_HN_BACKOFF,
                                           self.STAT_HN_UNKNOWN,
                                           self.STAT_USER_CREATED,
                                           self.STAT_GOOSE_FETCH,
                                           self.STAT_GOOSE_FAILURE))

    def fetch(self, hn_ids):
        """
            Given a list of hn ids, collect them
            if the ids correspond to articles their text will also be fetched
        """
        ret_list = []
        for aid in hn_ids:
            timer = time.time()
            self.STAT_TOTAL_REQUESTED += 1
            ret_list.append(self.fetch_me(aid))
            print('Fetched %s (%ss)' % (str(aid), str(round(time.time() - timer, 2))))

            if self.STAT_TOTAL_REQUESTED % 100 == 0:
                self.print_stats()
        return ret_list

    def goose_fetch(self, article_url):
        """Fetch the text from the given url"""
        self.STAT_GOOSE_FETCH += 1
        goose = Goose()
        try:
            goosed_article = goose.extract(url=str(article_url))
            text = '%s|||\n\n%s' % (
                goosed_article.cleaned_text,
                goosed_article.meta_description,
            )
            state = 0
        except Exception as e:
            traceback.print_exc(e)
            sys.stderr.write(str(e))
            state = 4
            text = None

        return text, state

    def db_fetch(self, hn_id):
        """Attempt to fetch from the db"""
        try:
            item = Article.objects.get(hn_id=hn_id)
            self.STAT_ARTICLE_FROM_DB += 1
        except Article.DoesNotExist:
            item = None
            # TODO Remove this hackery when article subclasses item
            try:
                item = Item.objects.get(hn_id=hn_id)
                self.STAT_ITEM_FROM_DB += 1
            except Item.DoesNotExist:
                pass

        return item

    def hn_fetch(self, article_id):
        """ Fetch the meta data from the hn api"""
        try:
            article_info = requests.get(ITEM_URL % article_id).json()
            self.STAT_HN_REQUEST += 1
        except Exception as e:
            print('Failed to get from hn api, backing off for 15s', e)
            time.sleep(15)
            article_info = None
            self.STAT_HN_BACKOFF += 1

        if article_info is None:
            self.STAT_HN_UNKNOWN += 1
            return Article.objects.create(
                hn_id=article_id,
                state=1,
                parsed=timezone.now()
            )
        submitter_id = article_info.get('by')
        if submitter_id is None:
            submitter_id = 'deleted'
        submitter, created = User.objects.get_or_create(id=submitter_id)

        if created:
            self.STAT_USER_CREATED += 1

        if article_info.get('type') != 'story':
            self.STAT_ITEM_FROM_HN += 1
            # Recurse to get the top_parent
            parent_id = article_info.get('parent')
            if parent_id is None:
                print('Failed to find the top parent for ' + str(article_id))
                self.STAT_ITEM_NO_TOP_PARENT += 1
                top_parent = None
                parent_item = None
            else:
                parent_item = self.fetch_me(parent_id)
                # When an article is returned, we know we've hit the top
                if isinstance(parent_item, Article):
                    # print('Found top parent' + str(parent_id))
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

            try:
                item = Item(
                    hn_id=article_id,
                    submitter=submitter,
                    type=article_info.get('type'),
                    parent=parent_item,
                    top_parent=top_parent
                )
                item.save()
                self.STAT_ITEM_CREATED += 1
            except OperationalError as e:
                self.STAT_INTEGRITY_ERROR += 1
                try:
                    item = Article.objects.get(hn_id=article_id)
                except Exception as e2:
                    print('Failed to get article after integrity error')
                    print(e2)
                    item = None
        else:
            self.STAT_ARTICLE_FROM_HN += 1
            url = article_info.get('url')
            if (not url) or url.startswith(
                    tuple(URL_EXCLUSIONS)):  # hack for goose as it doesnt like some unicode characters,
                # print("No url for article " + str(article_id))
                self.STAT_ARTICLE_NO_URL += 1
                state = 2
            else:
                state = 3
            try:
                title = article_info.get('title')
                if not title:
                    title = ''

                item = Article.objects.create(
                    hn_id=article_id,
                    state=state,
                    parsed=timezone.now(),
                    title=emoji_regex.sub(u'\uFFFD', title),
                    article_url=article_info.get('url'),
                    score=article_info.get('score'),
                    number_of_comments=article_info.get('descendants'),
                    submitter=submitter,
                    timestamp=article_info.get('time')
                )
                item.save()
                self.STAT_ARTICLE_CREATED += 1
            except OperationalError as e:
                try:
                    self.STAT_INTEGRITY_ERROR += 1
                    item = Article.objects.get(hn_id=article_id)
                except Exception as e2:
                    print('Failed to get article after integrity error')
                    print(e2)
                    item = None

        return item

    def fetch_me(self, hn_id):
        """Called recursively"""
        # First, attempt to load straight from db
        item = self.db_fetch(hn_id)

        if not item:
            # load the meta from HN
            item = self.hn_fetch(hn_id)

        if not isinstance(item, Article):
            return item
        else:
            article = item
            if article.state is None or article.state == 6 or article.state == 3:
                # Get the article text
                try:
                    (text, state) = self.goose_fetch(article.article_url)
                    if state is 0:
                        # Also strip emoji characters aka 4 byte chars
                        articletext = ArticleText(article=article,
                                                  text=emoji_regex.sub(u'\uFFFD', text),
                                                  parsed=timezone.now())
                        article.articletext = articletext
                        article.state = state
                        articletext.save()
                    else:
                        self.STAT_GOOSE_FAILURE += 1
                        article.state = state

                    article.save()
                except Exception as e:
                    self.STAT_GOOSE_FAILURE += 1
                    print("Failed to save prediction input to db for " + str(article.hn_id))
                    print(e)
                    article.state = 5
                    article.articletext = None
                    article.save()

            return article
