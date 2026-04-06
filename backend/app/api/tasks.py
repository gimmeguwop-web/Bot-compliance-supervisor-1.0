"""
API router for validation task management.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List

from app.db.session import get_session
from app.db.models import ValidationTask, TaskStatus, ValidationResult
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/", response_model=List[dict])
async def list_tasks(session: Session = Depends(get_session)):
    """List all validation tasks."""
    tasks = session.query(ValidationTask).all()
    return [
        {
            "id": task.id,
            "document_id": task.document_id,
            "profile_id": task.profile_id,
            "status": task.status,
            "progress": task.progress,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "error_message": task.error_message
        }
        for task in tasks
    ]


@router.get("/{task_id}", response_model=dict)
async def get_task(task_id: int, session: Session = Depends(get_session)):
    """Get details of a specific validation task including results."""
    task = session.query(ValidationTask).filter(ValidationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    results = session.query(ValidationResult).filter(ValidationResult.task_id == task_id).all()
    
    return {
        "id": task.id,
        "document_id": task.document_id,
        "profile_id": task.profile_id,
        "status": task.status,
        "progress": task.progress,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "error_message": task.error_message,
        "results": [
            {
                "id": r.id,
                "rule_id": r.rule_id,
                "rule_description": r.rule_description,
                "status": r.status,
                "severity": r.severity,
                "details": r.details,
                "page_ref": r.page_ref,
                "coordinates": r.coordinates,
                "gost_link": r.gost_link
            }
            for r in results
        ]
    }


@router.delete("/{task_id}", response_model=dict)
async def delete_task(task_id: int, session: Session = Depends(get_session)):
    """Delete a validation task and its results."""
    task = session.query(ValidationTask).filter(ValidationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Delete associated results first
    session.query(ValidationResult).filter(ValidationResult.task_id == task_id).delete()
    session.delete(task)
    session.commit()
    
    return {"message": f"Task {task_id} deleted successfully"}
