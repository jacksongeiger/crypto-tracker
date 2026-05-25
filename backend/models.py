import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class SourceType(str, enum.Enum):
    news_rss = "news_rss"
    on_chain = "on_chain"
    prediction_market = "prediction_market"
    macro = "macro"
    crypto_price = "crypto_price"


class Source(Base):
    __tablename__ = "sources"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name = Column(String, nullable=False)
    source_type = Column(
        Enum(SourceType, name="source_type", native_enum=True),
        nullable=False,
    )
    url = Column(String, nullable=True)
    config = Column(JSONB, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    raw_signals = relationship("RawSignal", back_populates="source")

    __table_args__ = (
        Index("ix_sources_source_type_is_active", "source_type", "is_active"),
    )


class RawSignal(Base):
    __tablename__ = "raw_signals"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    signal_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    url = Column(String, nullable=True)
    raw_payload = Column(JSONB, nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    ingested_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    extra = Column(JSONB, nullable=True)

    source = relationship("Source", back_populates="raw_signals")

    __table_args__ = (
        Index(
            "ix_raw_signals_source_occurred_at",
            "source_id",
            text("occurred_at DESC"),
        ),
        Index(
            "ix_raw_signals_ingested_at",
            text("ingested_at DESC"),
        ),
        Index(
            "uq_raw_signals_url",
            "url",
            unique=True,
            postgresql_where=text("url IS NOT NULL"),
        ),
    )


class Brief(Base):
    __tablename__ = "briefs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    generated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    brief_date = Column(Date, nullable=False)
    summary = Column(Text, nullable=False)
    model_used = Column(String, nullable=False)
    input_signal_count = Column(Integer, nullable=False)
    generation_metadata = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    themes = relationship(
        "BriefTheme",
        back_populates="brief",
        cascade="all, delete-orphan",
        order_by="BriefTheme.display_order",
    )

    __table_args__ = (
        Index("ix_briefs_brief_date", text("brief_date DESC")),
    )


class BriefTheme(Base):
    __tablename__ = "brief_themes"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    brief_id = Column(
        UUID(as_uuid=True),
        ForeignKey("briefs.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    conviction_score = Column(SmallInteger, nullable=True)
    primary_signal_id = Column(
        UUID(as_uuid=True),
        ForeignKey("raw_signals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_signal_ids = Column(JSONB, nullable=False)
    categories = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    # Which Source.source_type values contributed to this theme (multi-type
    # corroboration tracking introduced with synthesis v6). NULL for themes
    # produced before v6.
    source_types = Column(JSONB, nullable=True)
    display_order = Column(SmallInteger, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    brief = relationship("Brief", back_populates="themes")

    __table_args__ = (
        Index("ix_brief_themes_brief_order", "brief_id", "display_order"),
    )


class Subscriber(Base):
    """Daily-digest mailing list. Email is unique (case-insensitive via
    citext-style lower() index below). unsubscribed_at NULL = active.
    The daily_digest sender filters WHERE unsubscribed_at IS NULL.
    """

    __tablename__ = "subscribers"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    email = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    unsubscribed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Case-insensitive uniqueness — Gmail treats Jack@x and jack@x the
        # same and so do we. Functional unique index requires immutable
        # function call, which lower() is.
        Index(
            "uq_subscribers_email_lower",
            text("lower(email)"),
            unique=True,
        ),
        Index(
            "ix_subscribers_active",
            "unsubscribed_at",
            postgresql_where=text("unsubscribed_at IS NULL"),
        ),
    )
