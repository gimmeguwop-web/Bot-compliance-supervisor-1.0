"""
API router for report generation.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session
import os

from app.db.session import get_session
from app.db.models import ValidationTask
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter()


@router.get("/{task_id}/docx")
async def export_report_docx(task_id: int, session: Session = Depends(get_session)):
    """
    Export validation report as Word document (.docx).
    
    Implementation in PHASE 6.
    """
    task = session.query(ValidationTask).filter(ValidationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != "completed":
        raise HTTPException(status_code=400, detail="Task not completed yet")
    
    # Placeholder - will be implemented in PHASE 6
    raise HTTPException(status_code=501, detail="DOCX export not yet implemented")


@router.get("/{task_id}/xlsx")
async def export_report_xlsx(task_id: int, session: Session = Depends(get_session)):
    """
    Export validation report as Excel spreadsheet (.xlsx).
    
    Implementation in PHASE 6.
    """
    task = session.query(ValidationTask).filter(ValidationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != "completed":
        raise HTTPException(status_code=400, detail="Task not completed yet")
    
    # Placeholder - will be implemented in PHASE 6
    raise HTTPException(status_code=501, detail="XLSX export not yet implemented")
