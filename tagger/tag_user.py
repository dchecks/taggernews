import sys
import os

import requests
from django.core.wsgi import get_wsgi_application
from whitenoise.django import DjangoWhiteNoise
from django.utils import timezone
from goose import Goose

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    application = get_wsgi_application()
    application = DjangoWhiteNoise(application)
# Needs to be imported after django
from tagger.models import Article, User, Item
from tagger.management.commands.refresh_top_articles import ArticleFetcher

TOP_ARTICLES_URL = 'https://hacker-news.firebaseio.com/v0/user/'

arty = ArticleFetcher()
black_list = list(User.objects.filter(opt_out=True).values_list('id', flat=True))
black_list.append('deleted')


def refresh_user(user):
    user.articles = Article.objects.all().filter(submitter=user)
    user.items = Item.objects.all().filter(submitter=user)


def fetch_user(username):
    print('Fetching user ' + username)
    to_fetch = []

    if username not in black_list:
        user_info = requests.get(TOP_ARTICLES_URL + username + '.json').json()
        if not user_info:
            print('User doesn\'t exist, ' + username)
            return None
    else:
        print('User on blacklist, ' + username)
        return None

    user, created = User.objects.get_or_create(id=username)
    if created:
        print('Fetching unknown user:', username)
        to_fetch = user_info['submitted']
    else:
        for item_str in user_info['submitted']:
            item_id = int(item_str)
            if not user.has_cached(item_id):
                # havent found our id, must be new
                to_fetch.append(item_id)

    if to_fetch:
        print('Fetching ' + str(len(to_fetch)) + ' items for user ' + username)
        arty.fetch(to_fetch)
        refresh_user(user)
    else:
        print(username + ' needed no update')

    return user


def tag_user(articles):
    tags = {}
    for article in articles:
        for tag in article.tags.all():
            if not tag in tags:
                tags[tag] = 1
            else:
                tags[tag] += 1

    return tags

user = fetch_user('pg')
if user:
    all_articles = user.all_articles()
    print(tag_user(all_articles))
else:
    print('User doesn\'t exist')