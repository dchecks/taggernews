import sys
import os

import requests
from datetime import datetime, timedelta
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
USER_REFRESH_DELTA = timedelta(days=1)

arty = ArticleFetcher()
black_list = list(User.objects.filter(opt_out=True).values_list('id', flat=True))
black_list.append('deleted')


def refresh_user(user):
    user.articles = Article.objects.all().filter(submitter=user)
    user.items = Item.objects.all().filter(submitter=user)


def fetch_user(username):
    print('Fetching user ' + username)
    to_fetch = []

    if username in black_list:
        print('User on blacklist, ' + username)
        return None

    try:
        user = User.objects.get(id=username)
        threshold = timezone.now() - USER_REFRESH_DELTA
        if user.last_parsed is None or user.last_parsed < threshold:
            hn_refresh = True
        else:
            hn_refresh = False
    except User.DoesNotExist:
        hn_refresh = True

    if hn_refresh:
        user_info = requests.get(TOP_ARTICLES_URL + username + '.json').json()
        if not user_info:
            print('User doesn\'t exist, ' + username)
            return None
        user, created = User.objects.get_or_create(id=username, opt_out=False)
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

        user.last_parsed = timezone.now()
        user.opt_out = False  # TODO No idea why this isn't saving
        user.save()
    else:
        print('Using cached version of ' + username)
    return user


def tag_user(username):
    """Returns failure code and message or success and tags"""
    user = fetch_user(username)
    if user:
        tags = {}
        for article in user.all_articles():
            for tag in article.tags.all():
                if tag.name not in tags:
                    tags[tag.name] = 1
                else:
                    tags[tag.name] += 1

        return 200, tags
    else:
        return 404, 'User doesn\'t exist'

if __name__ == "__main__":
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            success, result = tag_user(str(arg))
            print(success, result)
