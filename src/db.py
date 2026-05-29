from typing import Generator
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine
from src.config import settings

connect_args = {"check_same_thread": False}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session