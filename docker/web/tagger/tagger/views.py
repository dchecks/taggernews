# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from operator import attrgetter
from django.shortcuts import render

from models import User
from tagger import fetch_user
from models import Article, Tag
from tagger import Session


def site_check(blocked, input):
    for site in blocked:
        if input.site() == site:
            return True
    return False


def news(request, page="1"):
    page_number = int(page)

    # TODO this will reshow the same results at the start of the page that were on the previous page,
    # if there are filtered results
    start = (page_number - 1) * 30
    end = min(page_number * 30 + 70, 300)
    ses = Session()

    articles = ses.query(Article).filter(Article.rank != None).order_by('rank')[start:end]
    user = ses.query(User).filter(User.id == "aunty_helen").first()

    articles = filter(site_check(user.blocked_sites, articles))

    context = {
        "articles": articles,
        "page_number": page_number,
        "offset": (page_number - 1) * 30,
        "base_path": "/news/"
    }
    r = render(request, 'article_list.html', context)
    ses.commit()
    return r


def user(request):
    context = {}
    uid = request.GET.get('id', None)

    ses = Session()
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
    r = render(request, 'user.html', context)
    ses.commit()
    return r


def by_tag(request, tag_string, page="1"):
    page_number = int(page)
    start = (page_number - 1) * 30
    end = page_number * 30

    tag_names = [tag_name.lower() for tag_name in tag_string.split('+')]

    logging.info(tag_names)

    ses = Session()
    tags = ses.query(Tag).filter(Tag.lowercase_name in tag_names).all()

    articles = ses.query(Article).filter(Article.tags in tags).order_by('rank')[start:end]
    # .prefetch_related('tags')

    context = {
        "articles": articles,
        "page_number": page_number,
        "offset": (page_number - 1) * 30,
        "base_path": "/tags/" + tag_string + "/"
    }

    r = render(request, 'article_list.html', context)
    ses.commit()
    return r


def all_tags(request):
    # TODO Re-enable this
    tags = []
    # ses = Session()
    # tags = ses.query(Tag).annotate(article_count=Count('article')).order_by('-article_count')

    context = {
        "tags": tags
    }

    return render(request, 'tag_list.html', context)


def blocked(request):

    ses = Session()
    user = ses.query(User).filter(User.id == "aunty_helen").first()

    context = {
        "blocked_sites": user.blocked
    }
    return render(request, 'block.html', context)