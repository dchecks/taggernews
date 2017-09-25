from __future__ import print_function
import requests
import sys

import time
from django.core.management.base import BaseCommand
from goose import Goose

from articles.models import Article

TOP_ARTICLES_URL = 'https://hacker-news.firebaseio.com/v0/topstories/.json'
ITEM_URL = 'https://hacker-news.firebaseio.com/v0/item/%s.json'


class ArticleFetcher:

    def __init__(self):
        pass

    def fetch_single(self, fetch_id):
        data = {fetch_id}
        articles, _, _, = self.fetch(data)
        if len(articles) is 1:
            return articles[0]
        else:
            return None

    def fetch(self, articles):
        update_count = 0
        create_count = 0
        ret_list = []
        for rank, article_id in enumerate(articles):
            print(article_id)
            article_info = requests.get(ITEM_URL % article_id).json()

            if article_info is None:
                print("HN id unknown ", article_id)
                article = Article.objects.create(
                    hn_id=article_id,
                    state=1,
                    parsed=time.time()
                )
            elif (not url) or url[:13] == "https://arxiv":
                print("No url for article ", article_id)
                article = Article.objects.create(
                    hn_id=article_id,
                    state=2,
                    parsed=time.time(),
                    title=article_info.get('title'),
                    article_url=article_info.get('url'), # still add it in case it's actually just bad
                    score=article_info.get('score'),
                    number_of_comments=article_info.get('descendants'),
                    submitter=article_info.get('by'),
                    timestamp=article_info.get('time'),
                    rank=rank,
                )
            else:
                url = article_info.get('url')
                try:
                    article = Article.objects.get(hn_id=article_id)
                    article.score = article_info.get('score')
                    article.number_of_comments = article_info.get('descendants')
                    article.rank = rank
                    if article.prediction_input is None or article.state is not 0:
                        goose = Goose()
                        print("getting " + url)
                        try:
                            goosed_article = goose.extract(url=url)
                            prediction_input = '%s|||\n\n%s' % (
                                goosed_article.cleaned_text,
                                goosed_article.meta_description,
                            )
                            article.prediction_input = prediction_input
                            article.state = 0
                        except:
                            article.prediction_input = None
                            article.state = 3
                            print("Failed to load text for ", url)
                    update_count += 1
                except Article.DoesNotExist:
                    print("goosing")
                    goose = Goose()
                    try:
                        print(url)
                        goosed_article = goose.extract(url=url)
                        prediction_input = '%s|||\n\n%s' % (
                            goosed_article.cleaned_text,
                            goosed_article.meta_description,
                        )
                        state = 0
                    except Exception as e:
                        sys.stderr.write(str(e))
                        state = 3

                    article = Article.objects.create(
                        hn_id=article_id,
                        state=state,
                        parsed=time.time(),
                        title=article_info.get('title'),
                        article_url=article_info.get('url'),
                        score=article_info.get('score'),
                        number_of_comments=article_info.get('descendants'),
                        submitter=article_info.get('by'),
                        timestamp=article_info.get('time'),
                        rank=rank,
                        prediction_input=prediction_input
                    )
                    create_count += 1
            article.save()
            ret_list.append(article)
            if rank % 10 == 0:
                message = "Added %s articles, updated %s articles..." % (create_count, update_count)
                print(message)

        # TODO eval need for this
        Article.objects.exclude(hn_id__in=articles).update(rank=None)

        return ret_list, create_count, update_count


class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def handle(self, *args, **options):
        top_article_ids = requests.get(TOP_ARTICLES_URL).json()

        (articles, create_count, update_count) = ArticleFetcher.fetch(top_article_ids)
        self.stdout.write(self.style.SUCCESS(
            'Done. Added: %s, Updated: %s' % (create_count, update_count)))
