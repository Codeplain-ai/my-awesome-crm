from typing import Sequence
from sqlmodel import Session, select, func, desc
from src.models.db import Record


class RecordRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, record: Record) -> Record:
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def list_by_type(self, data_type: str) -> Sequence[Record]:
        """Every stored row of a given data_type, regardless of source."""
        statement = select(Record).where(Record.data_type == data_type)
        return self.session.exec(statement).all()

    def delete_by_source(self, source: str) -> int:
        """Remove all rows produced by a given integration. Returns the count."""
        rows = self.session.exec(
            select(Record).where(Record.source == source)
        ).all()
        for row in rows:
            self.session.delete(row)
        return len(rows)

    def list_records(
        self,
        data_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[Record], int]:
        query = select(Record)
        if data_type is not None:
            query = query.where(Record.data_type == data_type)

        count_query = select(func.count()).select_from(query.subquery())
        total = self.session.exec(count_query).one()

        query = query.order_by(desc(Record.updated_at), Record.id)
        query = query.offset(offset).limit(limit)
        return self.session.exec(query).all(), total
