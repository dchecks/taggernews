from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

dbconn = "mysql://<USERNAME:PASSWORD@db:3306/tagger?charset=utf8mb4"
engine = create_engine(dbconn)
Session = scoped_session(sessionmaker(bind=engine))
