import os

from sqlalchemy import event
from sqlmodel import SQLModel, Session, create_engine

import models  # noqa: F401  (регистрирует таблицы в SQLModel.metadata)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/barbershop.db")

connect_args = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
