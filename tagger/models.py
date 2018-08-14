# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from urllib.parse import urlparse
from django.db import models

import datetime


class Tag(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=300)
    lowercase_name = models.CharField(max_length=300)

    def __unicode__(self):
        return self.name

    def get_relative_url(self):
        return "/tags/" + self.name.lower()


def func_top_parent(item):
    if hasattr(item, 'top_parent'):
        return item.top_parent
    else:
        return None


class User(models.Model):
    id = models.CharField(primary_key=True, max_length=15)

    # 0 Fresh
    # 1 Not found on HN
    # 5 Some exception
    # 10 tagged
    # 11 previously tagged, tag again
    # 13 tagging
    # 99 opt_out
    state = models.IntegerField(null=True, default=0)
    last_parsed = models.DateTimeField()
    priority = models.IntegerField()
    total_items = models.IntegerField(default=0)

    karma = models.IntegerField(null=True)
    born = models.DateTimeField()
    bio = models.CharField(max_length=2000)

    _article_cache = None
    _item_cache = None

    def __str__(self):
        return 'User ' + self.id \
               + ",\n state=" + str(self.state)\
               + ",\n last_parsed=" + str(self.last_parsed)\
               + ",\n priority=" + str(self.priority)

    def has_cached(self, hn_id):

        if not self._article_cache:
            self._article_cache = set()
            for article in self.article_set.all():
                self._article_cache.add(article.hn_id)
        if not self._item_cache:
            self._item_cache = set()
            for item in self.article_set.all():
                self._item_cache.add(item.hn_id)

        return hn_id in self._article_cache or hn_id in self._item_cache

    def all_articles(self):
        """Returns all articles this user has interacted with"""
        top_parents = map(func_top_parent, self.item_set.all())
        return list(filter(None, list(self.article_set.all()) + list(top_parents)))

    def get_tags(self):
        tags = {}
        for article in self.all_articles():
            for tag in article.tags.all():
                if tag.name not in tags:
                    tags[tag.name] = 1
                else:
                    tags[tag.name] += 1
        return tags


# db_constraint=False added for importer
class Item(models.Model):
    hn_id = models.IntegerField(primary_key=True)
    submitter = models.ForeignKey("User", db_column='submitter', on_delete=models.PROTECT)
    type = models.CharField(max_length=10)
    parent = models.ForeignKey("Item", db_column='parent', on_delete=models.PROTECT)
    top_parent = models.ForeignKey("Article", db_column='top_parent', on_delete=models.PROTECT)
    imported = models.BooleanField(default=False)


class Article(models.Model):
    hn_id = models.IntegerField(primary_key=True)

    # 0 successfully parsed,
    # 1 hn id not found,
    # 2 no url
    # 3 waiting for prediction_text parsing
    # 4 goose failure / no text
    # 5 db save failure of text
    # 6 parsing prediction text
    # 10 tagged
    # 11 processed for tagging, no tags assigned
    # 12 tagging error
    # 13 selected for tagging
    state = models.IntegerField(null=False)
    parsed = models.DateTimeField()
    title = models.CharField(max_length=2000)
    article_url = models.URLField(max_length=2000, null=True)
    score = models.IntegerField()
    number_of_comments = models.IntegerField(null=True)
    submitter = models.ForeignKey("User", db_column='submitter', on_delete=models.PROTECT)
    timestamp = models.IntegerField()
    tags = models.ManyToManyField(Tag, blank=True)
    rank = models.IntegerField(null=True)
    tagged = models.BooleanField(default=False)
    imported = models.BooleanField(default=False)

    def __unicode__(self):
        return self.title

    def site(self):
        if not self.article_url:
            return None
        else:
            netloc = urlparse(self.get_absolute_url()).netloc
            path = netloc.split(".")
            try:
                return path[-2] + "." + path[-1]
            except:
                return netloc

    def age(self):
        now = datetime.datetime.now()
        then = datetime.datetime.fromtimestamp(self.timestamp)
        delta = now - then
        if delta.seconds < 60:
            return str(delta.seconds) + " seconds"
        if delta.seconds < 3600:
            return str(delta.seconds / 60) + " minutes"
        return str(delta.seconds / 3600) + " hours"

    def get_absolute_url(self):
        return self.article_url or "https://news.ycombinator.com/item?id=" + str(self.hn_id)


class ArticleText(models.Model):
    article = models.OneToOneField(Article, on_delete=models.CASCADE, primary_key=True)
    parsed = models.DateTimeField()
    text = models.TextField(null=True)

    class Meta:
        db_table = 'tagger.article_text'