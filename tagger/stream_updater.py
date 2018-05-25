import os
import time
import logging

from datetime import datetime
from django.core.wsgi import get_wsgi_application
from whitenoise.django import DjangoWhiteNoise

import firebase
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
application = DjangoWhiteNoise(application)

from tagger.article_fetcher import ArticleFetcher

COMMENT_URL = "https://hacker-news.firebaseio.com/v0/updates.json"


class StreamUpdater:
    arty = ArticleFetcher()

    def __init__(self):
        pass

    def add(self, stream_text):
        message = stream_text[1]
        logging.info(datetime.now())
        logging.info('Data: ' + str(message))
        items = message['data']['items']
        items = self.arty.fetch(items)
        logging.info('Completed fetch of ' + str(len(items)))


updater = StreamUpdater()
comment_sub = firebase.subscriber(COMMENT_URL, updater.add)
comment_sub.start()
