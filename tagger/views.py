# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from operator import attrgetter

from django.db.models import Count
from django.shortcuts import render

from tagger.models import Article, Tag
from tagger.tag_user import fetch_user


def news(request, page="1"):
    page_number = int(page)

    start = (page_number - 1) * 30
    end = page_number * 30
    articles = Article.objects\
                        .all()\
                        .exclude(rank__isnull=True)\
                        .order_by('rank')\
                        .prefetch_related('tags', 'submitter')[start:end]

    context = {
        "articles": articles,
        "page_number": page_number,
        "offset": (page_number - 1) * 30,
        "base_path": "/news/"
    }

    return render(request, 'article_list.html', context)


def user(request):
    context = {}
    uid = request.GET.get('id', None)

    if uid:
        user = fetch_user(uid)
        if user:
            articles = user.all_articles()
            articles.sort(key=attrgetter("timestamp"))

            # Converts to a list of tuples, then sorts by tuple at index 1
            tags = sorted(user.get_tags().items(), key=lambda tup: tup[1])

            context = {
                "user": user,
                "articles": articles,
                "tags": tags,
            }
    return render(request, 'user.html', context)


def by_tag(request, tag_string, page="1"):
    page_number = int(page)
    start = (page_number - 1) * 30
    end = page_number * 30

    tag_names = [tag_name.lower() for tag_name in tag_string.split('+')]

    logging.info(tag_names)

    tags = Tag.objects.filter(lowercase_name__in=tag_names)

    articles = Article.objects.filter(tags__in=tags).order_by('rank').prefetch_related('tags')[start:end]

    context = {
        "articles": articles,
        "page_number": page_number,
        "offset": (page_number - 1) * 30,
        "base_path": "/tags/" + tag_string + "/"
    }
    return render(request, 'article_list.html', context)


def all_tags(request):
    tags = Tag.objects.annotate(article_count=Count('article')).order_by('-article_count')

    context = {
        "tags": tags
    }

    return render(request, 'tag_list.html', context)

