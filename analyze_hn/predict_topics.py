# Chris Riederer
# 2017-05-13

"""Predict topics using topic models or other stuff!"""
from joblib import Parallel, delayed
import pickle
import pandas as pd
from nltk import Counter
from os import listdir, environ
from os.path import isfile, join
import numpy

from dplython import *
from gensim import corpora, models, utils
from sklearn import linear_model, ensemble, feature_extraction, cross_validation, metrics

from django.core.wsgi import get_wsgi_application
from whitenoise.django import DjangoWhiteNoise

from utils import make_time_filename

environ.setdefault("DJANGO_SETTINGS_MODULE", "taggernews.settings")
application = get_wsgi_application()
application = DjangoWhiteNoise(application)
# Needs to be imported after django
from articles.models import Article
from articles.management.commands.refresh_top_articles import ArticleFetcher

RANDOM_FOREST_NAME = "./models/predictions/randomforest_model"
LOGISTIC_MODEL_NAME = "./models/predictions/logistic_model"

C_VALUE = 1.0
# If true will fetch articles that are not in the db, otherwise not include them in model
FETCH_NOT_CACHED = True

# Trained data
label_df = DplyFrame(pd.read_csv("supervised_topics.csv"))
# Built model
dictionary = corpora.Dictionary.load("./dictionaries/hn_dictionarySep24_0709.pkl")
lda = models.LdaModel.load("./models/generated/model_100topics_10passSep24_0710.gensim")


def label_article(text, trained_model):
    text = text.lower()
    tokens = list(utils.tokenize(text))
    bow = dictionary.doc2bow(tokens)
    return trained_model[bow]


def article_to_dict(text, trained_model):
    return {topic: weight for topic, weight in label_article(text, trained_model)}


def story_id_to_topicdict(article, trained_model=lda):
    """Given an article, read in the data and return the LDA topics as a
    dictionary of topic_id -> weight.
    """
    return article_to_dict(article.prediction_input, trained_model)


def create_logistic_model(df, _story_ids, data):
    results = []
    lr_models = {}
    for label in set(labels):
        positive_story_ids = set(df >> sift(X["labels"] == label) >> X.story_id.values)
        y_ = np.array([s in positive_story_ids for s in _story_ids])
        X_ = data
        lr = linear_model.LogisticRegression(C=C_VALUE)
        print(label, Counter(y_))

        cv_score = cross_validation.cross_val_score(
            lr, X_, y_, cv=10, scoring="roc_auc").mean()

        lr = lr.fit(X_, y_)
        lr_models[label] = lr
        probs = lr.predict_proba(X_)[:, 1]
        results.append({"alg": "log reg", "label": label, "auc": cv_score})
        print(C_VALUE, label, cv_score, len(probs[probs > 0.19]), Counter(labels == label))
        print()
    results_df = pd.DataFrame(results)

    lr_fname = make_time_filename(LOGISTIC_MODEL_NAME, ".pkl")
    print("writing file", lr_fname)
    with open(lr_fname, "wb") as f:
        pickle.dump(lr_models, f, protocol=2)


def create_random_forest_model(df, _story_ids, data):
    results = []
    rf_models = {}
    for label in set(labels):
        positive_story_ids = set(df >> sift(X["labels"] == label) >> X.story_id.values)
        y_ = np.array([s in positive_story_ids for s in _story_ids])
        X_ = data
        rf = ensemble.RandomForestClassifier(n_estimators=200)

        cv_score = cross_validation.cross_val_score(
            rf, X_, y_, cv=10, scoring="roc_auc").mean()

        rf.fit(X_, y_)
        rf_models[label] = rf
        this_output = {"alg": "random forest", "label": label, "auc": cv_score}
        print(this_output)
        results.append(this_output)
        print()
    results_df2 = pd.DataFrame(results)

    rf_fname = make_time_filename(RANDOM_FOREST_NAME, ".pkl")
    print("writing random forest file", rf_fname)
    with open(rf_fname, "wb") as f:
        pickle.dump(rf_models, f, protocol=2)


labels = []
topic_dicts = []
story_ids = []
story_id_to_topics = {}


def add_article(label, story_id, article):
    labels.append(label)
    story_ids.append(story_id)

    topic_dict = story_id_to_topicdict(article)
    topic_dicts.append(topic_dict)
    story_id_to_topics[story_id] = topic_dict
    print(label)


def load_article(label_df):
    skipped_due_state = 0
    uncached_articles = []

    for label, article_id in zip(label_df.topic, label_df.id):
        article_id = article_id.item()
        try:
            article = Article.objects.get(hn_id=article_id)
            if article.state is None:
                # reparse it again just to get a state assigned
                uncached_articles.append((label, article_id))
            elif article.state is not 0:
                skipped_due_state += 1
            else:
                add_article(label, article_id, article)
        except Article.DoesNotExist:
            uncached_articles.append((label, article_id))

    print("Uncached articles: ", len(uncached_articles))

    if FETCH_NOT_CACHED:
        print("Fetching articles...")
        for label, article_id in uncached_articles:
            print("Fetching " + str(article_id))
            article = ArticleFetcher().fetch_single(article_id)
            if article.state is not 0:
                print("Skipping article: " + str(article_id) + " due to state: " + article.state)
            else:
                add_article(label, article_id, article_id)
    else:
        print("Not attempting to fetch, set FETCH_NOT_CACHED if you want them, this can take a long time.")
    print("Skipped due to invalid state: " + skipped_due_state)


# Issue with requests in parallel mode
#zipped_list = zip(label_df.topic, label_df.id)
# Load supervised data in parallel as parsing can be slow
#Parallel(n_jobs=2)(delayed(load_article)(label, story_id) for label, story_id in zipped_list)

df = DplyFrame(pd.DataFrame({"labels": labels,
                             "story_id": story_ids,
                             "features": topic_dicts}))

labels = np.array(labels)
dict_vectorizer = feature_extraction.DictVectorizer()

story_ids2 = np.array(list(story_id_to_topics.keys()))
topic_data = np.array([[tdict.get(i, 0) for i in range(lda.num_topics)]
                       for tdict in story_id_to_topics.values()])

create_logistic_model(df, story_ids2, topic_data)
create_random_forest_model(df, story_ids2, topic_data)
