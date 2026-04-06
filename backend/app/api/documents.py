"""
API router for document upload and management.
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session
from typing import List
import uuid
import os

from app.db.session import get_session
from app.db.models import Document, ValidationTask, TaskStatus
from app.core.config import get_settings
from app.core.logging import get_logger
from app.workers.tasks import process_document_task

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter()


@router.post("/upload", response_model=dict)
async def upload_document(
    file: UploadFile = File(...),
    profile_id: str = "gost_2.104_basic",
    session: Session = Depends(get_session)
):
    """
    Upload a PDF document for validation.
    
    Args:
        file: PDF file to validate
        profile_id: ESKD profile ID to use for validation
        
    Returns:
        Task ID for tracking validation progress
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Validate file size (max 50MB)
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 50MB limit")
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(settings.STORAGE_PATH, unique_filename)
    
    # Ensure directory exists
    os.makedirs(settings.STORAGE_PATH, exist_ok=True)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file")
    
    # Create document record
    document = Document(
        filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        mime_type="application/pdf"
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    
    # Create validation task
    task = ValidationTask(
        document_id=document.id,
        profile_id=profile_id,
        status=TaskStatus.PENDING
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    
    # Queue Celery task
    try:
        process_document_task.delay(task.id, profile_id)
        logger.info(f"Queued validation task {task.id} for document {document.id}")
    except Exception as e:
        logger.error(f"Failed to queue Celery task: {e}")
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        session.commit()
        raise HTTPException(status_code=500, detail="Failed to queue validation task")
    
    return {
        "task_id": task.id,
        "document_id": document.id,
        "filename": file.filename,
        "status": "queued"
    }


@router.get("/", response_model=List[dict])
async def list_documents(session: Session = Depends(get_session)):
    """List all uploaded documents with their validation status."""
    documents = session.query(Document).all()
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "uploaded_at": doc.uploaded_at,
            "file_size": doc.file_size,
            "tasks": [
                {
                    "id": task.id,
                    "status": task.status,
                    "profile_id": task.profile_id,
                    "progress": task.progress
                }
                for task in doc.tasks
            ]
        }
        for doc in documents
    ]


@router.get("/{document_id}", response_model=dict)
async def get_document(document_id: int, session: Session = Depends(get_session)):
    """Get details of a specific document."""
    document = session.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "id": document.id,
        "filename": document.filename,
        "uploaded_at": document.uploaded_at,
        "file_size": document.file_size,
        "file_path": document.file_path,
        "tasks": [
            {
                "id": task.id,
                "status": task.status,
                "profile_id": task.profile_id,
                "progress": task.progress,
                "results_count": len(task.results)
            }
            for task in document.tasks
        ]
    }
