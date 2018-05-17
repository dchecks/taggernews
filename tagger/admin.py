# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from tagger.models import Article, Tag

# Register your models here.

admin.site.register(Article)
admin.site.register(Tag)