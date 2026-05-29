from sqlmodel import Session, select
from src.models.db import SourceLink

class SourceLinkRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, source_link: SourceLink) -> SourceLink:
        self.session.add(source_link)
        self.session.commit()
        self.session.refresh(source_link)
        return source_link

    def get_by_provider_external_id(self, provider_id: str, external_id: str) -> SourceLink | None:
        statement = select(SourceLink).where(
            SourceLink.provider_id == provider_id,
            SourceLink.external_id == external_id
        )
        return self.session.exec(statement).first()