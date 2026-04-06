"""
Database models for ESKD Validator.

Defines tables for documents, validation tasks, and results.
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """Status of a validation task."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ValidationResultStatus(str, Enum):
    """Status of a single validation rule check."""
    PASS = "pass"
    WARNING = "warning"
    ERROR = "error"


class Document(SQLModel, table=True):
    """Represents an uploaded document for validation."""
    __tablename__ = "documents"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str = Field(index=True)
    file_path: str
    file_size: int
    mime_type: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    tasks: List["ValidationTask"] = Relationship(back_populates="document")


class ValidationTask(SQLModel, table=True):
    """Represents a validation task for a document."""
    __tablename__ = "validation_tasks"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="documents.id", index=True)
    profile_id: str  # e.g., "gost_2.104_basic"
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # Relationships
    document: Document = Relationship(back_populates="tasks")
    results: List["ValidationResult"] = Relationship(back_populates="task")


class ValidationResult(SQLModel, table=True):
    """Result of a single rule validation check."""
    __tablename__ = "validation_results"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="validation_tasks.id", index=True)
    rule_id: str
    rule_description: str
    status: ValidationResultStatus
    severity: str  # error, warning, info
    details: Optional[str] = Field(sa_column_kwargs={"default": None})
    page_ref: Optional[int] = Field(default=None)  # Page number if applicable
    coordinates: Optional[str] = Field(default=None)  # JSON string with [x,y,w,h]
    gost_link: Optional[str] = None
    
    # Relationships
    task: ValidationTask = Relationship(back_populates="results")
