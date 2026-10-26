"""Database models for the URL shortener."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Link(Base):
    """A short code mapped to the original URL."""

    __tablename__ = "links"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, index=True, nullable=False)
    long_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Click(Base):
    """One asynchronously recorded redirect event."""

    __tablename__ = "clicks"
    __table_args__ = (Index("ix_clicks_link_id_clicked_at", "link_id", "clicked_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    link_id: Mapped[int] = mapped_column(ForeignKey("links.id"), nullable=False, index=True)
    clicked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    device: Mapped[str] = mapped_column(String(20), nullable=False)
    browser: Mapped[str] = mapped_column(String(50), nullable=False)
    ip_hash: Mapped[str] = mapped_column(String(64), nullable=False)
