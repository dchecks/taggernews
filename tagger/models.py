# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

try:
    from urllib import parse
except ImportError:
    from urlparse import urlparse as parse

import datetime


# Create your ml_models here.

class Tag(models.Model):
    name = models.CharField(max_length=300)
    lowercase_name = models.CharField(max_length=300)

    def __unicode__(self):
        return self.name

    def get_relative_url(self):
        return '/tags/' + self.name.lower()


class Article(models.Model):
    hn_id = models.IntegerField(primary_key=True)

    # null for backwards compat,
    # 0 successfully parsed,
    # 1 hn id not found,
    # 2 no url
    # 3 waiting for prediction_text parsing
    # 4 goose failure / no text
    state = models.IntegerField(null=True)
    parsed = models.DateTimeField()
    title = models.CharField(max_length=1500)
    article_url = models.URLField(max_length=1000, null=True)
    score = models.IntegerField()
    number_of_comments = models.IntegerField(null=True)
    submitter = models.CharField(max_length=500)
    timestamp = models.IntegerField()
    tags = models.ManyToManyField(Tag, blank=True)
    rank = models.IntegerField(null=True)
    tagged = models.BooleanField(default=False)
    prediction_input = models.TextField(null=True)

    def __unicode__(self):
        return self.title

    def site(self):
        if not self.article_url:
            return None
        else:
            netloc = parse(self.get_absolute_url()).netloc
            path = netloc.split(".")
            try:
                return path[-2] + "." + path[-1]
            except:
                return netloc

    def age(self):
        now = datetime.datetime.now()
        then = datetime.datetime.fromtimestamp(self.timestamp)
        delta = now - then
        if (delta.seconds < 60):
            return str(delta.seconds) + " seconds"
        if (delta.seconds < 3600):
            return str(delta.seconds / 60) + " minutes"
        return str(delta.seconds / 3600) + " hours"

    def get_absolute_url(self):
        return self.article_url or "https://news.ycombinator.com/item?id=" + str(self.hn_id)
