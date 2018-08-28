import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from stream.models import User, Article, Tag, Item
from test import dbconn_test, test_user, test_article


class TestModelLoading(unittest.TestCase):
    engine = create_engine(dbconn_test)
    Session = sessionmaker(bind=engine)

    def setUp(self):
        self.ses = self.Session()

    def user(self):
        return self.ses.query(User).filter(User.id == test_user).first()

    def test_tags_loaded(self):
        tags = self.ses.query(Tag).all()

        self.assertTrue(len(tags) > 0)
        print(("Loaded %s tags" % str(len(tags))))

    def test_tags_rel_url(self):
        tag = self.ses.query(Tag).first()

        self.assertTrue(tag.name.lower() in tag.get_relative_url())

    def test_user(self):
        user = self.user()
        self.assertTrue(user)

    def test_article(self):
        article = self.ses.query(Article).filter(Article.hn_id == test_article).first()
        self.assertTrue(article)

    def test_article_user_mapping(self):
        article = self.ses.query(Article).filter(Article.hn_id == test_article).first()
        self.assertTrue(article)

        self.assertTrue(article.submitter)

    def test_article_text_mapping(self):
        article = self.ses.query(Article).filter(Article.hn_id == test_article).first()
        self.assertTrue(article)

        self.assertTrue(article.text)
        print("Length of text: " + str(len(article.text.text)))

    def test_article_tag_mapping(self):
        article = self.ses.query(Article).filter(Article.hn_id == test_article).first()
        self.assertTrue(article)

        self.assertTrue(len(article.tags) > 0)

    def test_user_item_mapping(self):
        user = self.ses.query(User).filter(User.id == test_user).first()

        self.assertTrue(len(user.items) > 0)
        print(user.items[0].submitter)
        self.assertTrue(user.items[0].submitter == user)

    def test_user_article_mapping(self):
        user = self.ses.query(User).filter(User.id == test_user).first()

        self.assertTrue(len(user.articles) > 0)
        self.assertTrue(user.articles[0].submitter == user)

    def test_item_parent_mapping(self):
        item = self.ses.query(Item).filter(Item.parent != None).first()

        self.assertTrue(item.parent)
        self.assertTrue(isinstance(item.parent, Item))

    def test_item_top_parent_mapping(self):
        item = self.ses.query(Item).filter(Item.top_parent != None).first()

        self.assertTrue(item.top_parent)
        self.assertTrue(isinstance(item.top_parent, Article))

    def user_all_articles_is_superset(self):
        user = self.user()
        self.assertTrue(user)

        all_articles = user.all_articles()
        articles = user.articles

        self.assertFalse(all_articles == articles, "Articles and all_articles are equal")
        self.assertTrue(set.issubset(all_articles, articles), "Articles is not a subset")

    def user_all_articles_contains_other_submitters(self):
        user = self.user()

        all_articles = user.all_articles()
        submitter_different = False
        for article in all_articles:
            if article.submitter != user:
                submitter_different = True

        self.assertTrue(submitter_different, "None of the articles in the superset were submitted by another user")

    def user_tag_compilation(self):
        user = self.user()
        tags = user.get_tags()

        self.assertTrue(len(tags) > 0)

if __name__ == '__main__':
    unittest.main()
