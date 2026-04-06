"""
Celery tasks for document validation pipeline.

Implements the main processing workflow:
1. Parse PDF
2. Run rule engine
3. Perform OCR/CV checks
4. LLM semantic analysis (optional)
5. Generate reports
"""
from typing import Any, Dict, List
from celery import chain, group
from app.workers.celery_app import celery_app
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def process_document_task(self, task_id: int, profile_id: str):
    """
    Main task orchestrating the full validation pipeline.
    
    Args:
        task_id: ID of the ValidationTask in database
        profile_id: ID of the ESKD profile to use (e.g., "gost_2.104_basic")
    """
    try:
        logger.info(f"Starting validation task {task_id} with profile {profile_id}")
        
        # Update task status to PROCESSING
        # This would interact with the database via a service layer
        # For now, we'll implement the core logic in subsequent phases
        
        # Step 1: Parse PDF and extract metadata
        parse_result = parse_pdf_task.delay(task_id)
        
        # Step 2: Run rule engine checks
        rule_checks = run_rule_engine_task.si(task_id, profile_id)
        
        # Step 3: CV/OCR checks for signatures and stamps
        cv_checks = run_cv_ocr_task.si(task_id, profile_id)
        
        # Step 4: LLM semantic analysis (if enabled)
        llm_analysis = run_llm_analysis_task.si(task_id)
        
        # Step 5: Compile results and update task status
        finalize_task = compile_results_task.si(task_id)
        
        # Chain the tasks
        workflow = chain(
            parse_result,
            rule_checks,
            cv_checks,
            llm_analysis,
            finalize_task
        )
        
        result = workflow.apply_async()
        
        return {"status": "started", "workflow_id": result.id}
        
    except Exception as exc:
        logger.error(f"Error starting validation task {task_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task
def parse_pdf_task(task_id: int) -> Dict[str, Any]:
    """Parse PDF document and extract text/metadata."""
    logger.info(f"Parsing PDF for task {task_id}")
    
    from app.db.session import get_db_session
    from app.engines.parser.pdf_parser import PDFParser
    from app.services.document_service import DocumentService
    
    try:
        db = next(get_db_session())
        
        # Get task and document info
        doc_service = DocumentService(db)
        task_data = doc_service.get_task_info(task_id)
        
        if not task_data:
            raise ValueError(f"Task {task_id} not found")
        
        file_path = task_data["file_path"]
        document_id = task_data["document_id"]
        
        # Parse PDF
        parser = PDFParser()
        parsed_doc = parser.parse(file_path)
        
        # Save parsed data to database
        doc_service.save_parsed_data(document_id, parsed_doc)
        
        logger.info(f"Successfully parsed PDF for task {task_id}: {parsed_doc.page_count} pages")
        
        return {"status": "parsed", "pages": parsed_doc.page_count}
        
    except Exception as e:
        logger.error(f"Failed to parse PDF for task {task_id}: {e}")
        raise
    finally:
        db.close()


@celery_app.task
def run_rule_engine_task(task_id: int, profile_id: str) -> Dict[str, Any]:
    """Run ESKD/GOST rule checks."""
    logger.info(f"Running rule engine for task {task_id}, profile {profile_id}")
    
    from app.db.session import get_db_session
    from app.engines.rules.loader import RuleLoader
    from app.engines.rules.validator import RuleValidator
    from app.services.document_service import DocumentService
    
    try:
        db = next(get_db_session())
        doc_service = DocumentService(db)
        
        # Get parsed document data
        parsed_doc = doc_service.get_parsed_data(task_id)
        if not parsed_doc:
            raise ValueError(f"No parsed data found for task {task_id}")
        
        # Load rules profile
        loader = RuleLoader()
        profile = loader.load_profile(profile_id)
        
        if not profile:
            logger.warning(f"Profile {profile_id} not found, using default")
            profile = loader.load_profile("gost_2.105_basic")
        
        # Run validation
        validator = RuleValidator()
        results = validator.validate(parsed_doc, profile)
        
        # Save results to database
        doc_service.save_validation_results(task_id, results)
        
        logger.info(f"Rule engine completed: {len(results)} checks performed")
        
        return {"status": "rules_checked", "checks_count": len(results)}
        
    except Exception as e:
        logger.error(f"Rule engine failed for task {task_id}: {e}")
        raise
    finally:
        db.close()


@celery_app.task
def run_cv_ocr_task(task_id: int, profile_id: str) -> Dict[str, Any]:
    """Run computer vision and OCR checks for signatures and stamps."""
    logger.info(f"Running CV/OCR for task {task_id}")
    
    from app.db.session import get_db_session
    from app.engines.vision.detector import SignatureDetector
    from app.engines.vision.ocr_engine import OCREngine
    from app.engines.vision.validator import SignatureValidator
    from app.services.document_service import DocumentService
    
    try:
        db = next(get_db_session())
        doc_service = DocumentService(db)
        
        # Get parsed document data
        parsed_doc = doc_service.get_parsed_data(task_id)
        if not parsed_doc:
            raise ValueError(f"No parsed data found for task {task_id}")
        
        # Detect signature zones
        detector = SignatureDetector()
        detected_zones = detector.detect(parsed_doc.file_path)
        
        # Run OCR on detected zones
        ocr_engine = OCREngine(lang=settings.OCR_LANG.split(","))
        ocr_results = []
        for zone in detected_zones:
            text = ocr_engine.recognize(zone.image)
            zone.text = text
            ocr_results.append(zone)
        
        # Validate signatures (check required roles)
        validator = SignatureValidator()
        validation_results = validator.validate_signatures(ocr_results, profile_id)
        
        # Update parsed_doc with signature data
        parsed_doc.signatures = ocr_results
        
        # Save results
        doc_service.save_parsed_data(task_id, parsed_doc)  # Update signatures
        doc_service.save_validation_results(task_id, validation_results)
        
        logger.info(f"CV/OCR completed: {len(ocr_results)} signatures detected")
        
        return {"status": "cv_ocr_complete", "signatures_found": len(ocr_results)}
        
    except Exception as e:
        logger.error(f"CV/OCR failed for task {task_id}: {e}")
        raise
    finally:
        db.close()


@celery_app.task
def run_llm_analysis_task(task_id: int) -> Dict[str, Any]:
    """Run LLM semantic analysis."""
    logger.info(f"Running LLM analysis for task {task_id}")
    
    from app.db.session import get_db_session
    from app.engines.llm.provider import get_llm_provider
    from app.engines.llm.analyzer import LLMAnalyzer
    from app.services.document_service import DocumentService
    
    try:
        db = next(get_db_session())
        doc_service = DocumentService(db)
        
        # Check if LLM is enabled
        if not settings.LLM_ENABLED:
            logger.info("LLM analysis disabled, skipping")
            return {"status": "llm_disabled"}
        
        # Get parsed document and existing results
        parsed_doc = doc_service.get_parsed_data(task_id)
        if not parsed_doc:
            raise ValueError(f"No parsed data found for task {task_id}")
        
        existing_results = doc_service.get_validation_results(task_id)
        
        # Initialize LLM provider
        llm_provider = get_llm_provider(
            provider_type=settings.LLM_PROVIDER,
            base_url=settings.LLM_BASE_URL,
            model_name=settings.LLM_MODEL_NAME,
            api_key=settings.LLM_API_KEY,
        )
        
        # Run analysis
        analyzer = LLMAnalyzer(llm_provider)
        llm_results = await analyzer.analyze_document(parsed_doc, existing_results)
        
        # Convert and save results
        if llm_results:
            validation_results = LLMAnalyzer.convert_to_validation_results(
                llm_results, 
                doc_service.get_document_id_by_task(task_id)
            )
            doc_service.save_validation_results(task_id, validation_results)
        
        logger.info(f"LLM analysis completed: {len(llm_results)} findings")
        
        return {"status": "llm_complete", "findings_count": len(llm_results)}
        
    except Exception as e:
        logger.error(f"LLM analysis failed for task {task_id}: {e}")
        # Graceful degradation: don't fail the whole task
        return {"status": "llm_failed", "error": str(e)}
    finally:
        db.close()


@celery_app.task
def compile_results_task(task_id: int) -> Dict[str, Any]:
    """Compile all results and mark task as complete."""
    logger.info(f"Compiling results for task {task_id}")
    
    from app.db.session import get_db_session
    from app.services.document_service import DocumentService
    
    try:
        db = next(get_db_session())
        doc_service = DocumentService(db)
        
        # Get all validation results
        results = doc_service.get_validation_results(task_id)
        
        # Calculate summary statistics
        total = len(results)
        errors = sum(1 for r in results if r.status.value == "error")
        warnings = sum(1 for r in results if r.status.value == "warning")
        passed = total - errors - warnings
        
        # Update task status
        doc_service.complete_task(task_id, {
            "total_checks": total,
            "errors": errors,
            "warnings": warnings,
            "passed": passed,
        })
        
        logger.info(f"Task {task_id} completed: {errors} errors, {warnings} warnings, {passed} passed")
        
        return {
            "status": "completed",
            "summary": {
                "total": total,
                "errors": errors,
                "warnings": warnings,
                "passed": passed,
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to compile results for task {task_id}: {e}")
        raise
    finally:
        db.close()
