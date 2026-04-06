"""
Document service for managing document validation workflow.

Provides database operations for:
- Document upload and storage
- Task management
- Parsed data persistence
- Validation results storage
"""
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, update
import json
import logging

from app.db.models import Document, ValidationTask, ValidationResult, ValidationStatus, ParsedData
from app.engines.parser.pdf_parser import ParsedDocument

logger = logging.getLogger(__name__)


class DocumentService:
    """Service layer for document-related database operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_document(self, filename: str, file_path: str, file_size: int, mime_type: str) -> Document:
        """Create a new document record."""
        doc = Document(
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        logger.info(f"Created document {doc.id}: {filename}")
        return doc

    def create_validation_task(self, document_id: int, profile_id: str) -> ValidationTask:
        """Create a new validation task for a document."""
        task = ValidationTask(
            document_id=document_id,
            profile_id=profile_id,
            status=ValidationStatus.PENDING,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        logger.info(f"Created validation task {task.id} for document {document_id}")
        return task

    def get_task_info(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get task information including document details."""
        task = self.db.get(ValidationTask, task_id)
        if not task:
            return None
        
        doc = self.db.get(Document, task.document_id)
        if not doc:
            return None
        
        return {
            "task_id": task.id,
            "document_id": doc.id,
            "file_path": doc.file_path,
            "filename": doc.filename,
            "profile_id": task.profile_id,
            "status": task.status.value,
        }

    def save_parsed_data(self, document_id: int, parsed_doc: ParsedDocument) -> None:
        """Save parsed document data to database."""
        # Check if already exists
        existing = self.db.query(ParsedData).filter(
            ParsedData.document_id == document_id
        ).first()
        
        # Serialize parsed data
        data_dict = {
            "page_count": parsed_doc.page_count,
            "metadata": parsed_doc.metadata or {},
            "text_content": parsed_doc.text_content or [],
            "title_block": parsed_doc.title_block.dict() if parsed_doc.title_block else None,
            "signatures": [sig.dict() for sig in (parsed_doc.signatures or [])],
            "tables": parsed_doc.tables or [],
            "file_path": parsed_doc.file_path,
        }
        
        if existing:
            existing.data = data_dict
            existing.status = "completed"
        else:
            parsed_data = ParsedData(
                document_id=document_id,
                data=data_dict,
                status="completed",
            )
            self.db.add(parsed_data)
        
        self.db.commit()
        logger.info(f"Saved parsed data for document {document_id}")

    def get_parsed_data(self, task_id: int) -> Optional[ParsedDocument]:
        """Get parsed document data for a task."""
        task = self.db.get(ValidationTask, task_id)
        if not task:
            return None
        
        parsed_data = self.db.query(ParsedData).filter(
            ParsedData.document_id == task.document_id
        ).first()
        
        if not parsed_data:
            return None
        
        # Reconstruct ParsedDocument from stored data
        data = parsed_data.data
        return ParsedDocument(
            filename=self.db.get(Document, task.document_id).filename if self.db.get(Document, task.document_id) else "",
            page_count=data.get("page_count", 0),
            metadata=data.get("metadata", {}),
            text_content=data.get("text_content", []),
            title_block=None,  # Would need proper reconstruction
            signatures=[],  # Would need proper reconstruction
            tables=data.get("tables", []),
            file_path=data.get("file_path", ""),
        )

    def save_validation_results(self, task_id: int, results: List[Dict[str, Any]]) -> None:
        """Save validation results to database."""
        task = self.db.get(ValidationTask, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        for result_data in results:
            # Convert details dict to JSON string
            details_json = json.dumps(result_data.get("details", {}))
            
            result = ValidationResult(
                task_id=task_id,
                document_id=task.document_id,
                rule_id=result_data.get("rule_id", "unknown"),
                rule_name=result_data.get("rule_name", "Unknown Rule"),
                status=ValidationStatus(result_data.get("status", "info")),
                message=result_data.get("message", ""),
                details=details_json,
                page_ref=result_data.get("page_ref"),
                gost_link=result_data.get("gost_link"),
            )
            self.db.add(result)
        
        self.db.commit()
        logger.info(f"Saved {len(results)} validation results for task {task_id}")

    def get_validation_results(self, task_id: int) -> List[ValidationResult]:
        """Get all validation results for a task."""
        results = self.db.query(ValidationResult).filter(
            ValidationResult.task_id == task_id
        ).all()
        return results

    def get_document_id_by_task(self, task_id: int) -> Optional[int]:
        """Get document ID by task ID."""
        task = self.db.get(ValidationTask, task_id)
        return task.document_id if task else None

    def complete_task(self, task_id: int, summary: Dict[str, Any]) -> None:
        """Mark a validation task as completed with summary statistics."""
        task = self.db.get(ValidationTask, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = ValidationStatus.COMPLETED
        task.summary = json.dumps(summary)
        
        self.db.commit()
        logger.info(f"Completed task {task_id} with summary: {summary}")

    def get_task_status(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get current task status."""
        task = self.db.get(ValidationTask, task_id)
        if not task:
            return None
        
        return {
            "task_id": task.id,
            "status": task.status.value,
            "profile_id": task.profile_id,
            "summary": json.loads(task.summary) if task.summary else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }
