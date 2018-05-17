# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render

from tagger.models import Article, Tag
from tagger.tag_user import tag_user, fetch_user


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


def user(request, username):

    user = fetch_user(username)

    articles = user.all_articles()
    articles.sort()  # TODO chrono comparator

    context = {
        "user": user,
        "tags": user.get_tags(),
        "articles": articles,
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


def user(request):
    username = request.GET.get('id', '')
    code, result = tag_user(username)
    return JsonResponse(result, status=code)
