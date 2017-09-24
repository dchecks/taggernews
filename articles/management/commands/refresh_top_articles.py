from __future__ import print_function
from django.core.management.base import BaseCommand, CommandError
import requests
import sys

from articles.models import Article

from goose import Goose
import json

TOP_ARTICLES_URL = 'https://hacker-news.firebaseio.com/v0/topstories/.json'
ITEM_URL = 'https://hacker-news.firebaseio.com/v0/item/%s.json'


class ArticleFetcher():

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
            try:
                article = Article.objects.get(hn_id=article_id)
                article.score = article_info.get('score')
                article.number_of_comments = article_info.get('descendants')
                article.rank = rank
                if article.prediction_input is None:
                    goose = Goose()
                    url = article.article_url
                    if (not url) or url[:13] == "https://arxiv":
                        continue
                    print("getting " + url)
                    try:
                        goosed_article = goose.extract(url=url)
                        prediction_input = '%s|||\n\n%s' % (
                            goosed_article.cleaned_text,
                            goosed_article.meta_description,
                        )
                        article.prediction_input = prediction_input
                    except:
                        article.prediction_input = None
                        print("Failed to load text for ", url)
                article.save()
                update_count += 1
            except Article.DoesNotExist:
                try:
                    print("goosing")
                    goose = Goose()
                    url = article_info.get('url')
                    if (not url) or url[:13] == "https://arxiv":
                        continue
                    print(url)
                    goosed_article = goose.extract(url=url)
                    prediction_input = '%s|||\n\n%s' % (
                        goosed_article.cleaned_text,
                        goosed_article.meta_description,
                    )
                    article = Article.objects.create(
                        hn_id=article_id,
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
                except Exception as e:
                    sys.stderr.write(str(e))
                    continue

            ret_list.append(article)
            if rank % 10 == 0:
                message = "Added %s articles, updated %s articles..." % (
                    create_count, update_count)
                print(message)

        Article.objects.exclude(hn_id__in=articles).update(rank=None)

        return ret_list, create_count, update_count


class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def handle(self, *args, **options):
        top_article_ids = requests.get(TOP_ARTICLES_URL).json()

        (articles, create_count, update_count) = ArticleFetcher.fetch(top_article_ids)
        self.stdout.write(self.style.SUCCESS(
            'Done. Added: %s, Updated: %s' % (create_count, update_count)))
