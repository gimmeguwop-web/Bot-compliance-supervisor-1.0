"""
Celery tasks for document validation pipeline.
Orchestrates parsing, rule checking, CV/OCR, LLM analysis, and report generation.
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from celery import Task
from app.core.logger import logger
from app.db.session import SessionLocal
from app.models.document import Document, ValidationTask, TaskStatus, ValidationResult
from app.engines.parser.pdf_parser import PDFParser
from app.engines.rules.rule_engine import RuleEngine
from app.engines.vision.signature_detector import SignatureDetector
from app.engines.llm.analyzer import LLMAnalyzer
from app.engines.export.report_generator import ReportGenerator
from app.api.routes.websockets import broadcast_task_update
from app.core.config import settings

from .celery_app import celery_app


class ValidationTaskBase(Task):
    """Base task with database session."""
    _db = None
    
    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db
    
    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(base=ValidationTaskBase, bind=True)
async def validate_document_task(self, task_id: int, document_id: int, profile_id: str):
    """
    Main validation task that orchestrates the entire pipeline.
    
    Pipeline stages:
    1. Parse PDF (extract text, metadata, coordinates)
    2. Run rule-based checks (ESKD/GOST)
    3. Detect signatures and stamps (CV + OCR)
    4. LLM semantic analysis (if enabled)
    5. Generate reports (DOCX + XLSX)
    6. Update task status and results
    """
    db = self.db
    
    # Get task and document from DB
    task = db.query(ValidationTask).filter(ValidationTask.id == task_id).first()
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not task or not document:
        logger.error(f"Task {task_id} or Document {document_id} not found")
        return {"error": "Task or Document not found"}
    
    # Update task status to processing
    task.status = TaskStatus.PROCESSING
    task.progress = 0
    db.commit()
    
    all_results: List[Dict[str, Any]] = []
    metadata = {
        "task_id": str(task.id),
        "timestamp": datetime.now(),
        "profile": profile_id,
        "document_name": document.original_filename
    }
    
    try:
        # Stage 1: Parse PDF
        logger.info(f"Task {task_id}: Starting PDF parsing for {document.file_path}")
        await broadcast_task_update(str(task_id), {
            "stage": "parsing",
            "progress": 10,
            "message": "Извлечение текста и метаданных из PDF..."
        })
        
        parser = PDFParser()
        parsed_data = await parser.parse(document.file_path)
        
        if not parsed_data:
            raise ValueError("Failed to parse PDF")
        
        task.progress = 20
        db.commit()
        
        # Stage 2: Rule-based checks
        logger.info(f"Task {task_id}: Running rule engine with profile {profile_id}")
        await broadcast_task_update(str(task_id), {
            "stage": "rules",
            "progress": 40,
            "message": f"Проверка по профилю ЕСКД: {profile_id}"
        })
        
        rule_engine = RuleEngine()
        rule_results = await rule_engine.validate(parsed_data, profile_id)
        all_results.extend(rule_results)
        
        task.progress = 50
        db.commit()
        
        # Stage 3: Signature detection (CV + OCR)
        logger.info(f"Task {task_id}: Detecting signatures and stamps")
        await broadcast_task_update(str(task_id), {
            "stage": "vision",
            "progress": 65,
            "message": "Поиск подписей и штампов..."
        })
        
        signature_detector = SignatureDetector()
        vision_results = await signature_detector.detect(document.file_path, parsed_data)
        all_results.extend(vision_results)
        
        task.progress = 75
        db.commit()
        
        # Stage 4: LLM semantic analysis (if enabled)
        if settings.LLM_PROVIDER and settings.LLM_PROVIDER != "none":
            logger.info(f"Task {task_id}: Running LLM semantic analysis")
            await broadcast_task_update(str(task_id), {
                "stage": "llm",
                "progress": 85,
                "message": "Семантический анализ текстовых требований..."
            })
            
            llm_analyzer = LLMAnalyzer()
            llm_results = await llm_analyzer.analyze(parsed_data, profile_id)
            all_results.extend(llm_results)
        
        task.progress = 90
        db.commit()
        
        # Stage 5: Save results to DB
        logger.info(f"Task {task_id}: Saving {len(all_results)} results to database")
        for result_data in all_results:
            result = ValidationResult(
                task_id=task_id,
                rule_id=result_data.get('rule_id', ''),
                description=result_data.get('description', ''),
                status=result_data.get('status', 'unknown'),
                details=result_data.get('details'),
                page_ref=result_data.get('page_ref'),
                gost_link=result_data.get('gost_link'),
                confidence=result_data.get('confidence'),
                check_type=result_data.get('check_type', '')
            )
            db.add(result)
        db.commit()
        
        # Stage 6: Generate reports
        logger.info(f"Task {task_id}: Generating reports")
        await broadcast_task_update(str(task_id), {
            "stage": "export",
            "progress": 95,
            "message": "Генерация отчётов DOCX и XLSX..."
        })
        
        generator = ReportGenerator()
        report_paths = generator.generate_reports(
            document.original_filename,
            all_results,
            metadata
        )
        
        # Update task with report paths
        task.docx_report_path = report_paths.get('docx')
        task.xlsx_report_path = report_paths.get('xlsx')
        
        # Finalize task
        errors_count = sum(1 for r in all_results if r.get('status') == 'error')
        warnings_count = sum(1 for r in all_results if r.get('status') == 'warning')
        
        task.status = TaskStatus.COMPLETED
        task.progress = 100
        task.errors_count = errors_count
        task.warnings_count = warnings_count
        task.completed_at = datetime.now()
        db.commit()
        
        logger.info(f"Task {task_id} completed successfully with {errors_count} errors and {warnings_count} warnings")
        
        await broadcast_task_update(str(task_id), {
            "stage": "completed",
            "progress": 100,
            "message": "Проверка завершена",
            "results_summary": {
                "total": len(all_results),
                "errors": errors_count,
                "warnings": warnings_count,
                "passed": len(all_results) - errors_count - warnings_count
            },
            "reports": report_paths
        })
        
        return {
            "task_id": task_id,
            "status": "completed",
            "results_count": len(all_results),
            "errors": errors_count,
            "warnings": warnings_count,
            "reports": report_paths
        }
        
    except Exception as e:
        logger.exception(f"Task {task_id} failed with error: {e}")
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        task.completed_at = datetime.now()
        db.commit()
        
        await broadcast_task_update(str(task_id), {
            "stage": "failed",
            "progress": 0,
            "message": f"Ошибка: {str(e)}"
        })
        
        return {"task_id": task_id, "status": "failed", "error": str(e)}


@celery_app.task(base=ValidationTaskBase, bind=True)
async def cleanup_old_tasks(self, days: int = 30):
    """Cleanup old completed/failed tasks and associated files."""
    from datetime import timedelta
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    db = self.db
    result = db.query(ValidationTask).filter(
        ValidationTask.completed_at < cutoff_date
    ).delete(synchronize_session=False)
    
    db.commit()
    logger.info(f"Cleaned up {result} old tasks older than {days} days")
    
    return {"cleaned": result}


__all__ = ["validate_document_task", "cleanup_old_tasks"]
