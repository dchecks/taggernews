# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from urllib.parse import urlparse

import datetime

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Boolean, Text
from datetime import datetime
from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy_utils import URLType

Base = declarative_base()


class Tag(Base):
    __tablename__ = "tagger_tag"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String(length=300))
    lowercase_name = Column(String(length=300))

    def __unicode__(self):
        return self.name

    def get_relative_url(self):
        return "/tags/" + self.name.lower()


article_tags_table = Table('tagger_article_tags', Base.metadata,
                           Column('article_id', Integer, ForeignKey('tagger_article.hn_id')),
                           Column('tag_id', Integer, ForeignKey('tagger_tag.id'))
                           )


class User(Base):
    __tablename__ = "tagger_user"
    id = Column(String(15), primary_key=True)

    # 0 Fresh
    # 1 Not found on HN
    # 5 Some exception
    # 10 tagged
    # 11 previously tagged, tag again
    # 13 tagging
    # 99 opt_out
    state = Column(Integer(), default=0)
    last_parsed = Column(DateTime())
    priority = Column(Integer())
    total_items = Column(Integer(), default=0)

    karma = Column(Integer())
    born = Column(DateTime())
    bio = Column(String(2000))

    items = relationship("Item")
    articles = relationship("Article")

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
class Item(Base):
    __tablename__ = "tagger_item"
    hn_id = Column(Integer(), primary_key=True)

    type = Column(String(10))
    imported = Column(Boolean(), default=False)

    submitter_id = Column(String(15), ForeignKey("tagger_user.id"))
    parent_id = Column(Integer, ForeignKey('tagger_item.hn_id'))
    top_parent_id = Column(Integer, ForeignKey('tagger_article.hn_id'))

    submitter = relationship("User", back_populates="items")
    parent = relationship("Item", remote_side=[hn_id])
    top_parent = relationship("Article")


class Article(Base):
    __tablename__ = "tagger_article"
    hn_id = Column(Integer(), primary_key=True)

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
    state = Column(Integer(), nullable=False)
    parsed = Column(DateTime())
    title = Column(String(2000))
    article_url = Column(URLType(), nullable=True)
    score = Column(Integer())
    number_of_comments = Column(Integer(), nullable=True)
    timestamp = Column(Integer())
    rank = Column(Integer(), nullable=True)
    tagged = Column(Boolean(), default=False)
    imported = Column(Boolean(), default=False)

    submitter_id = Column(String(15), ForeignKey("tagger_user.id"))
    submitter = relationship("User", back_populates="articles")

    text = relationship("ArticleText", uselist=False, back_populates="article")
    tags = relationship("Tag", secondary=article_tags_table)

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


class ArticleText(Base):
    __tablename__ = 'tagger_article_text'

    article_id = Column(Integer, ForeignKey("tagger_article.hn_id"), primary_key=True)
    article = relationship("Article", back_populates="text")

    parsed = Column(DateTime())
    text = Column(Text(), nullable=True)


def func_top_parent(item):
    if hasattr(item, 'top_parent'):
        return item.top_parent
    else:
        return None
