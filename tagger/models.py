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
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=300)
    lowercase_name = models.CharField(max_length=300)

    def __unicode__(self):
        return self.name

    def get_relative_url(self):
        return "/tags/" + self.name.lower()


def func_top_parent(item):
    return item.top_parent


class User(models.Model):
    id = models.CharField(primary_key=True, max_length=15)
    opt_out = models.BooleanField(default=False)
    last_parsed = models.DateTimeField()
    priority = models.IntegerField()
    tagged = models.BooleanField(default=False)

    def has_cached(self, hn_id):
        for article in self.article_set.all():
            if article.hn_id == hn_id:
                return True
        for item in self.item_set.all():
            if item.hn_id == hn_id:
                return True

    def all_articles(self):
        """Returns all articles this user has interacted with"""
        top_parents = map(func_top_parent, self.item_set.all())
        return list(self.article_set.all()) + top_parents

    def get_tags(self):
        tags = {}
        for article in self.all_articles():
            for tag in article.tags.all():
                if tag.name not in tags:
                    tags[tag.name] = 1
                else:
                    tags[tag.name] += 1
        return tags


class Item(models.Model):
    hn_id = models.IntegerField(primary_key=True)
    submitter = models.ForeignKey("User", db_column='submitter', on_delete=models.PROTECT)
    type = models.CharField(max_length=10)
    parent = models.ForeignKey("Item", db_column='parent', on_delete=models.PROTECT)
    top_parent = models.ForeignKey("Article", db_column='top_parent', on_delete=models.PROTECT)


class Article(models.Model):
    hn_id = models.IntegerField(primary_key=True)

    # null for backwards compat,
    # 0 successfully parsed,
    # 1 hn id not found,
    # 2 no url
    # 3 waiting for prediction_text parsing
    # 4 goose failure / no text
    # 5 db save failure of text
    # 10 tagged
    # 11 processed for tagging, no tags assigned
    # 12 tagging error
    state = models.IntegerField(null=True)
    parsed = models.DateTimeField()
    title = models.CharField(max_length=1500)
    article_url = models.URLField(max_length=1000, null=True)
    score = models.IntegerField()
    number_of_comments = models.IntegerField(null=True)
    submitter = models.ForeignKey("User", db_column='submitter', on_delete=models.PROTECT)
    timestamp = models.IntegerField()
    tags = models.ManyToManyField(Tag, blank=True)
    rank = models.IntegerField(null=True)
    tagged = models.BooleanField(default=False)


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


class ArticleText(models.Model):
    article = models.OneToOneField(Article, on_delete=models.CASCADE, primary_key=True)
    parsed = models.DateTimeField()
    text = models.TextField(null=True)
