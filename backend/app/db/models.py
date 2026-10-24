import enum
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PageStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    ERROR = "ERROR"


class RunType(str, enum.Enum):
    FULL = "FULL"
    TRANSLATE_ONLY = "TRANSLATE_ONLY"


class RunStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


class ReviewStatus(str, enum.Enum):
    PENDING = "PENDING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REVIEWED = "REVIEWED"


class BlockSource(str, enum.Enum):
    AUTO = "AUTO"
    MANUAL = "MANUAL"


class Orientation(str, enum.Enum):
    VERTICAL = "VERTICAL"
    HORIZONTAL = "HORIZONTAL"


class Work(Base):
    __tablename__ = "works"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    folders: Mapped[list["Folder"]] = relationship(back_populates="work")
    characters: Mapped[list["Character"]] = relationship(back_populates="work")


class Folder(Base):
    __tablename__ = "folders"
    __table_args__ = (UniqueConstraint("name", name="uq_folders_name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    work_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("works.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    work: Mapped["Work | None"] = relationship(back_populates="folders")
    pages: Mapped[list["Page"]] = relationship(
        back_populates="folder", cascade="all, delete-orphan"
    )


class Page(Base):
    __tablename__ = "pages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    folder_id: Mapped[UUID] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    height: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    page_number: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[PageStatus] = mapped_column(
        Enum(PageStatus, name="page_status"),
        nullable=False,
        default=PageStatus.PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    folder: Mapped["Folder"] = relationship(back_populates="pages")
    character_mentions: Mapped[list["CharacterMention"]] = relationship(
        back_populates="page", cascade="all, delete-orphan"
    )
    processing_runs: Mapped[list["ProcessingRun"]] = relationship(
        back_populates="page", cascade="all, delete-orphan"
    )
    text_blocks: Mapped[list["TextBlock"]] = relationship(
        back_populates="page", cascade="all, delete-orphan"
    )


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    work_id: Mapped[UUID] = mapped_column(
        ForeignKey("works.id", ondelete="CASCADE"), nullable=False
    )
    name_original: Mapped[str] = mapped_column(String(255), nullable=False)
    name_preferred: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(50), nullable=True)
    speech_register: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    work: Mapped["Work"] = relationship(back_populates="characters")
    mentions: Mapped[list["CharacterMention"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )


class CharacterMention(Base):
    __tablename__ = "character_mentions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    page_id: Mapped[UUID] = mapped_column(
        ForeignKey("pages.id", ondelete="CASCADE"), nullable=False
    )
    text_block_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("text_blocks.id", ondelete="SET NULL"), nullable=True
    )

    character: Mapped["Character"] = relationship(back_populates="mentions")
    page: Mapped["Page"] = relationship(back_populates="character_mentions")
    text_block: Mapped["TextBlock | None"] = relationship(back_populates="character_mentions")


class ProcessingRun(Base):
    __tablename__ = "processing_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    page_id: Mapped[UUID] = mapped_column(
        ForeignKey("pages.id", ondelete="CASCADE"), nullable=False
    )
    run_type: Mapped[RunType] = mapped_column(Enum(RunType, name="run_type"), nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status"),
        nullable=False,
        default=RunStatus.PENDING,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    page: Mapped["Page"] = relationship(back_populates="processing_runs")
    text_blocks: Mapped[list["TextBlock"]] = relationship(back_populates="processing_run")


class TextBlock(Base):
    __tablename__ = "text_blocks"
    __table_args__ = (
        CheckConstraint("type IN ('#', '$')", name="ck_text_blocks_type"),
        UniqueConstraint(
            "page_id",
            "order_number",
            name="uq_text_blocks_page_order",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    page_id: Mapped[UUID] = mapped_column(
        ForeignKey("pages.id", ondelete="CASCADE"), nullable=False
    )
    processing_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("processing_runs.id", ondelete="SET NULL"), nullable=True
    )
    order_number: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str | None] = mapped_column(String(1), nullable=True)
    original: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    bbox: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    lines: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    orientation: Mapped[Orientation | None] = mapped_column(
        Enum(Orientation, name="orientation"), nullable=True
    )
    ruby: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    handwritten: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status"),
        nullable=False,
        default=ReviewStatus.PENDING,
    )
    source: Mapped[BlockSource] = mapped_column(
        Enum(BlockSource, name="block_source"),
        nullable=False,
        default=BlockSource.AUTO,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    page: Mapped["Page"] = relationship(back_populates="text_blocks")
    processing_run: Mapped["ProcessingRun | None"] = relationship(back_populates="text_blocks")
    translation_suggestions: Mapped[list["TranslationSuggestion"]] = relationship(
        back_populates="text_block", cascade="all, delete-orphan"
    )
    character_mentions: Mapped[list["CharacterMention"]] = relationship(back_populates="text_block")


class TranslationSuggestion(Base):
    __tablename__ = "translation_suggestions"
    __table_args__ = (
        CheckConstraint("relevance BETWEEN 1 AND 5", name="ck_translation_suggestions_relevance"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    text_block_id: Mapped[UUID] = mapped_column(
        ForeignKey("text_blocks.id", ondelete="CASCADE"), nullable=False
    )
    translation: Mapped[str] = mapped_column(Text, nullable=False)
    observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevance: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    source: Mapped[BlockSource] = mapped_column(
        Enum(BlockSource, name="block_source"),
        nullable=False,
        default=BlockSource.AUTO,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    text_block: Mapped["TextBlock"] = relationship(back_populates="translation_suggestions")
