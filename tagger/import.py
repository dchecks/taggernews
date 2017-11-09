import json
import os
from operator import sub

import time
from django.utils import timezone

from django.db import connection
from django.db.transaction import atomic
import ijson
from ijson import parse
from django.core.wsgi import get_wsgi_application
from whitenoise.django import DjangoWhiteNoise

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    application = get_wsgi_application()
    application = DjangoWhiteNoise(application)
# Needs to be imported after django
from tagger.models import Article, User, Item


class Importer:
    create_count = 0
    d_create = 0
    skip_count = 0
    d_skip = 0
    user_count = 0
    d_user = 0
    error_count = 0
    d_error = 0
    timer = time.time()
    d_time = time.time()

    def __init__(self):
        pass

    def print_stats(self):
        print('%s (+%s): Scanned %s items, created %s (+%s), skipped %s (+%s), new users %s (+%s), errors %s (+%s)' %
              (time.time() - self.timer, time.time() - self.d_time,
               self.create_count + self.skip_count,
               self.create_count, self.create_count - self.d_create,
               self.skip_count, self.skip_count - self.d_skip,
               self.user_count, self.user_count - self.d_user,
               self.error_count, self.error_count - self.d_error)
              )
        self.d_time = time.time()
        self.d_create = self.create_count
        self.d_skip = self.skip_count
        self.d_user = self.user_count
        self.d_error = self.error_count

    def import_items(self, offset=0):
        with open('resources/HNCommentsAll.json') as data_file:
            with connection.cursor() as cursor:
                for outerItem in ijson.items(data_file, "item"):
                    for hit in outerItem['hits']:
                        if (self.create_count + self.skip_count) % 1000 == 0:
                            self.print_stats()

                        if self.skip_count < offset:
                            self.skip_count += 1
                            continue

                        cmd = ""
                        hn_id = None
                        submitter = None
                        parent = None
                        top_parent = None

                        try:
                            hn_id = hit['objectID']
                            if Item.objects.filter(hn_id=hn_id).exists():
                                self.skip_count += 1
                                continue

                            if 'author' in hit:
                                submitter = hit['author']
                            elif 'deleted' in hit:
                                submitter = 'deleted'

                            if 'parent' in hit:
                                parent = hit['parent_id']
                            else:
                                parent = 'NULL'

                            if 'story_id' in hit:
                                top_parent = hit['story_id']
                            else:
                                top_parent = 'NULL'

                            # Create the user the old fashioned way if necessary
                            user, created = User.objects.get_or_create(id=hit['author'])
                            if created:
                                self.user_count += 1
                                user.save()

                            cmd = "INSERT INTO tagger_item (hn_id, type, submitter, parent, top_parent, imported) " \
                                "VALUES(%s, 'comment', '%s', %s, %s, 1)" % (hn_id, submitter, parent, top_parent)
                            cursor.execute(cmd)
                            self.create_count += 1
                        except Exception as e:
                            print('Exception, hn_id: ' + str(hn_id))
                            print(e)
                            print('last cmd: ' + cmd)
                            self.print_stats()

    def import_articles(self):
        with open('../resources/HNStoriesAll.json', buffering=4096000) as data_file:
            with connection.cursor() as cursor:
                state = 3

                for outerItem in ijson.items(data_file, "item"):
                    for hit in outerItem['hits']:
                        hn_id = hit['objectID']

                        if Article.objects.filter(hn_id=hn_id).exists():
                            self.skip_count += 1
                            continue

                        title = None
                        url = None
                        score = None
                        number_of_comments = None
                        submitter = None
                        timestamp = None

                        try:
                            title = hit['title']
                            url = hit['url']
                            score = hit['points']
                            number_of_comments = hit['num_comments']
                            submitter = hit['author']
                            timestamp = hit['created_at_i']

                            user, created = User.objects.get_or_create(id=hit['author'])
                            if created:
                                self.user_count += 1
                                user.save()

                            cmd = "INSERT INTO tagger_article (hn_id, title, state, article_url, score, number_of_comments, submitter, timestamp) " \
                                  "VALUES(%s, %s, %s, %s, %s, %s, %s, %s)"
                            cursor.execute(cmd, (hn_id, title, str(state), url, score, number_of_comments, submitter, timestamp))
                            self.create_count += 1
                        except Exception as e:
                            print('Exception, hn_id: ' + str(hn_id))
                            print(e)
                            print('last cmd: ' + cmd)
                            self.print_stats()


    def scan(self, file, hn_id):
        hn_id = str(hn_id)
        counter = 0
        print_count = 0
        print('Scanning for ' + str(hn_id))
        for outerItem in ijson.items(file, "item"):
            for hit in outerItem['hits']:
                if hn_id == hit['objectID']:
                    print_count = 2
                if print_count > 0:
                    print(hit['objectID'])
                    print(hit)
                    print_count -= 1
                counter += 1
                if counter % 10000 == 0:
                    print('Progress: ' + str(counter))


Importer().import_articles()
# with open('resources/HNCommentsAll.json', buffering=4096000) as data_file:
#     Importer().import_items(5845000)
#     #Importer().scan(data_file, 7076238)
# Importer().scan(data_file, 7076239)


