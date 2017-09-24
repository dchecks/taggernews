import pickle
import random

from django.core.management.base import BaseCommand, CommandError
from gensim import corpora, models, utils
from goose import Goose
from sklearn.externals import joblib
import numpy as np
import requests
import sys

from articles.models import Article, Tag


class TextTagger(object):
    """Object which tags articles. Needs topic modeler and """

    def __init__(self, topic_modeler, gensim_dict, lr_dict, threshold=0.5):
        super(TextTagger, self).__init__()
        self.topic_modeler = topic_modeler
        self.gensim_dict = gensim_dict
        self.lr_dict = lr_dict
        self.threshold = threshold

    def text_to_topic_list(self, text):
        text = text.lower()
        tokens = list(utils.tokenize(text))
        bow = self.gensim_dict.doc2bow(tokens)
        return self.topic_modeler[bow]

    def text_to_numpy(self, text):
        out = np.zeros(self.topic_modeler.num_topics)
        for idx, val in self.text_to_topic_list(text):
            out[idx] = val
        return out

    def text_to_topic_dict(self, text):
        return {topic: weight for topic, weight in self.label_article(text)}

    def text_to_tags(self, text):
        input_vect = np.array([self.text_to_numpy(text)])
        tags = []
        for label, lr_model in self.lr_dict.items():
            tag_prob = lr_model.predict_proba(input_vect)[0, 1]
            if tag_prob > self.threshold:
                tags.append(label)

        return tags

    @classmethod
    def init_from_files(cls, topic_model_fname, gensim_dict_fname, lr_dict_fname,
                        *args, **kwargs):
        topic_modeler = models.ldamodel.LdaModel.load(topic_model_fname)
        gensim_dict = corpora.Dictionary.load(gensim_dict_fname)
        lr_dict = joblib.load(lr_dict_fname)
        return cls(topic_modeler, gensim_dict, lr_dict, *args, **kwargs)


text_tagger = TextTagger.init_from_files(
    "analyze_hn/model_100topics_10passSep19_1205.gensim",
    "analyze_hn/hn_dictionarySep19_1201.pkl",
    "articles/model/serialized_model/rf_models.pkl",
    threshold=0.3,
)


class Command(BaseCommand):
    help = 'tags articles'

    def handle(self, *args, **options):
        articles = Article.objects.filter(
            article_url__isnull=False)

        for i, article in enumerate(articles):
            try:
                prediction_input = article.prediction_input
                if prediction_input is None:
                    raise Exception("No prediction_input")

                # Make tag predictions
                prediction_input = prediction_input.encode('utf-8')
                predicted_tags = text_tagger.text_to_tags(prediction_input)

            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    'Failed to tag article %s. Error: %s.' % (
                        article.hn_id, e)))
                continue

            # Make tag predictions
            prediction_input = prediction_input.decode('utf-8')
            predicted_tags = text_tagger.text_to_tags(prediction_input)

            # Add tags to db (only matters if there's a previously unseen tag)
            existing_tags = Tag.objects.filter(name__in=predicted_tags)
            new_tags = set(predicted_tags) - set([t.name for t in existing_tags])
            new_tags = Tag.objects.bulk_create([Tag(name=t, lowercase_name=t.lower()) for t in new_tags])

            # Associate tags with article (many-to-many)
            article_tags = list(existing_tags) + new_tags
            article_tags = Tag.objects.filter(id__in=[t.id for t in article_tags])
            article.tags.add(*article_tags)

            article.tagged = True
            article.save()

            self.stdout.write(self.style.SUCCESS(
                'Tagged article %s (%s of %s)\n%s\n%s' % (
                    article.hn_id, i + 1, articles.count(), article.title, article_tags)
            ))
