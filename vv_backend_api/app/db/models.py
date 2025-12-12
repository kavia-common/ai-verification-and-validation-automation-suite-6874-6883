"""
SQLAlchemy ORM models for the V&V automation system.

Entities:
- SRS: A software requirements specification document (text or path)
- TestCase: Structured test case generated from SRS
- Script: A test script (e.g., pytest/Playwright) generated for a TestCase
- Run: An execution run (batch) of multiple test cases/scripts
- TestResult: Result of executing a Script within a Run
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from . import Base


class TimestampMixin:
    """Common created_at and updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class SRS(Base, TimestampMixin):
    """SRS document that can be the source for generating test cases."""

    __tablename__ = "srs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # content can hold markdown/plaintext of SRS, or path to uploaded file if stored on disk
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    test_cases: Mapped[List["TestCase"]] = relationship(
        "TestCase",
        back_populates="srs",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_srs_title", "title"),
    )


class TestCase(Base, TimestampMixin):
    """Structured test case generated from an SRS."""

    __tablename__ = "test_case"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    srs_id: Mapped[int] = mapped_column(
        ForeignKey("srs.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g., P0/P1
    tags: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # comma-separated tags

    srs: Mapped["SRS"] = relationship("SRS", back_populates="test_cases")

    scripts: Mapped[List["Script"]] = relationship(
        "Script",
        back_populates="test_case",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_test_case_srs_id", "srs_id"),
        Index("ix_test_case_name", "name"),
        UniqueConstraint("srs_id", "name", name="uq_test_case_srs_name"),
    )


class Script(Base, TimestampMixin):
    """A generated test script (e.g., pytest/Playwright) for a test case."""

    __tablename__ = "script"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_case_id: Mapped[int] = mapped_column(
        ForeignKey("test_case.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    language: Mapped[str] = mapped_column(String(50), nullable=False, default="python")
    framework: Mapped[str] = mapped_column(String(100), nullable=False, default="pytest-playwright")
    # The actual script content (e.g., pytest file content) or a path reference
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    test_case: Mapped["TestCase"] = relationship("TestCase", back_populates="scripts")

    results: Mapped[List["TestResult"]] = relationship(
        "TestResult",
        back_populates="script",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_script_test_case_id", "test_case_id"),
        Index("ix_script_framework", "framework"),
    )


class Run(Base, TimestampMixin):
    """An execution run (batch) where multiple scripts may be executed."""

    __tablename__ = "run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")  # pending, running, completed, failed
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    triggered_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # user or system

    results: Mapped[List["TestResult"]] = relationship(
        "TestResult",
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_run_status", "status"),
        Index("ix_run_label", "label"),
    )


class TestResult(Base, TimestampMixin):
    """Execution result of a script within a run."""

    __tablename__ = "test_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("run.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    script_id: Mapped[int] = mapped_column(
        ForeignKey("script.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # passed, failed, skipped, error, pending
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # assertion message, error logs, etc.
    artifacts_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)  # screenshots, videos, etc.

    run: Mapped["Run"] = relationship("Run", back_populates="results")
    script: Mapped["Script"] = relationship("Script", back_populates="results")

    __table_args__ = (
        Index("ix_test_result_run_id", "run_id"),
        Index("ix_test_result_script_id", "script_id"),
        Index("ix_test_result_outcome", "outcome"),
        UniqueConstraint("run_id", "script_id", name="uq_test_result_run_script"),
    )
