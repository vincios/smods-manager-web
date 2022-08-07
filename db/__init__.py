from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

from smods_manager.app import db_path

db_path = db_path
metadata = MetaData()
Base = declarative_base(metadata=metadata)

flask_db = SQLAlchemy(metadata=metadata)
engine = create_engine(f'sqlite:///{db_path}')


# We have to create a SQLAlchemy scoped session for the install_mod task to reuse the same session object in each
# recursion step. Otherwise, each recursion step creates a new session ans, when sqlite reach a limit on opened sessions
# (or sqlite reaches a timeout for an opened session?), SQLAlchemy raise a "database is locked" exception. See:
# https://stackoverflow.com/questions/63704426/threading-and-recursion-problem-using-sqlite-with-sqlalchemy-in-a-flask-api-call
# https://docs.sqlalchemy.org/en/13/orm/contextual.html
session_factory = sessionmaker(bind=engine)
SSession = scoped_session(session_factory)
