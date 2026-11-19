from sqlalchemy import Boolean, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class StreamDraft(Base):
    __tablename__ = "stream_drafts"
    stream_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(255))
    baseline: Mapped[list] = mapped_column(JSON, default=list)
    offers: Mapped[list] = mapped_column(JSON, default=list)
    dirty: Mapped[bool] = mapped_column(Boolean, default=False)
    conflict: Mapped[bool] = mapped_column(Boolean, default=False)
