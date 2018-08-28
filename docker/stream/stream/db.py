from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

dbconn = "mysql://<USERNAME:PASSWORD@db:3306/tagger?charset=utf8mb4"
engine = create_engine(dbconn)
Session = sessionmaker(bind=engine)


def session_factory():
    return Session

