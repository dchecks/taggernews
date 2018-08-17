from django.db import connections
from django.http import HttpResponse


def something(request):
    c = connections['state_db'].cursor()
    c.execute("select id from tagger_user limit 1")
    rows = c.fetchall()
    name = rows[0]["id"]

    return HttpResponse("" + name)
