import sys
import os

import requests
from datetime import datetime, timedelta, time
from django.core.wsgi import get_wsgi_application
from whitenoise.django import DjangoWhiteNoise
from django.utils import timezone

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    application = get_wsgi_application()
    application = DjangoWhiteNoise(application)
# Needs to be imported after django
from tagger.models import Article, User, Item
from tagger.management.commands.refresh_top import ArticleFetcher

USER_URL = 'https://hacker-news.firebaseio.com/v0/user/'
USER_REFRESH_DELTA = timedelta(days=1)

arty = ArticleFetcher()
black_list = list(User.objects.filter(opt_out=True).values_list('id', flat=True))
black_list.append('deleted')


def refresh_user(user):
    user.articles = Article.objects.all().filter(submitter=user)
    user.items = Item.objects.all().filter(submitter=user)


class UserTagger:
    BATCH_SIZE = 50
    tagged_users = 0

    def __init__(self):
        pass

    def tag(self, infinite=False):
        while True:
            users = User.objects.all().filter(opt_out=False).exclude(priority=None).order_by('priority')[:self.BATCH_SIZE]
            remaining = self.BATCH_SIZE - len(users)
            users = list(users) + list(User.objects.all().filter(opt_out=False, priority=None)[:remaining])
            if len(users) == 0:
                print('No users left to tag')
                if infinite:
                    print('Sleeping...')
                    time.sleep(10)
                else:
                    print("Quitting...")
                    break
            else:
                print('Tagging user batch of ' + str(len(users)))
                for user in users:
                    username = user.id
                    user_info = requests.get(USER_URL + username + '.json').json()
                    to_fetch = []
                    for item_str in user_info['submitted']:
                        item_id = int(item_str)
                        if not user.has_cached(item_id):
                            # havent found our id in the db, must be new
                            to_fetch.append(item_id)
                    if to_fetch:
                        print('Fetching ' + str(len(to_fetch)) + ' items for user ' + username)
                        arty.fetch(to_fetch)
                        refresh_user(user)
                    else:
                        print(username + ' needed no update')

                    user.last_parsed = timezone.now()
                    user.priority = None
                    user.save()
                    self.tagged_users += 1

            print('Finished tagging user batch of ' + str(len(users)))
            print('Total users tagged: ' + str(self.tagged_users))


def fetch_user(username):
    print('Fetching user ' + username)

    if username in black_list:
        print('User on blacklist, ' + username)
        return None

    try:
        user = User.objects.get(id=username)
        threshold = timezone.now() - USER_REFRESH_DELTA
        if user.last_parsed and user.last_parsed < threshold:
            print('User cache expired, ' + username)
            user.tagged = False
        elif user.tagged:
            print('Using cached version of ' + username)
            return user
    except User.DoesNotExist:
        user_info = requests.get(USER_URL + username + '.json').json()
        if not user_info:
            print('User doesn\'t exist, ' + username)
            return None
        print('Creating user, ' + username)
        user = User(id=username, opt_out=False, tagged=False, last_parsed=None)

    user.save()
    return user


def tag_user(username):
    """Returns failure code and message or success and tags"""
    user = fetch_user(username)
    if user and user.last_parsed is not None:
        tags = user.get_tags()
        return 200, tags
    elif not user:
        return 404, {'message': 'User unavailable'}
    else:
        return 204, {'message': 'User not yet parsed, check back soon'}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            success, result = tag_user(str(arg))
            print(success, result)
    else:
        UserTagger().tag(True)
