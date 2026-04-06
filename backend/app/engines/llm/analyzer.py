from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.db.models import Document, ValidationResult, ValidationStatus
from app.engines.llm.provider import LLMProvider, LLMAnalysisResult
from app.engines.parser.pdf_parser import ParsedDocument

logger = logging.getLogger(__name__)


class LLMAnalyzer:
    """
    Модуль семантического анализа документов с помощью LLM.
    
    Анализирует извлеченные данные на предмет:
    - Смысловых противоречий
    - Логических несоответствий
    - Отсутствия обязательных требований
    - Рекомендаций по улучшению
    """

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    async def analyze_document(
        self,
        parsed_doc: ParsedDocument,
        existing_results: List[ValidationResult],
    ) -> List[LLMAnalysisResult]:
        """
        Выполнить семантический анализ документа.
        
        Args:
            parsed_doc: Распарсенный документ с текстом и метаданными
            existing_results: Результаты детерминированных проверок (Rule Engine)
            
        Returns:
            Список результатов LLM-анализа
        """
        # Формирование контекста для LLM
        context = self._build_context(parsed_doc, existing_results)
        
        if not context.strip():
            logger.warning("Empty context for LLM analysis, skipping")
            return []
        
        logger.info(f"Sending context to LLM ({len(context)} chars)")
        
        # Вызов LLM
        results = await self.llm_provider.analyze(context)
        
        logger.info(f"LLM returned {len(results)} findings")
        
        return results

    def _build_context(
        self,
        parsed_doc: ParsedDocument,
        existing_results: List[ValidationResult],
    ) -> str:
        """
        Построить текстовый контекст для отправки в LLM.
        
        Включает:
        - Метаданные документа
        - Извлеченный текст (сгруппированный по секциям)
        - Данные из основной надписи
        - Результаты предыдущих проверок (для контекста)
        """
        sections = []
        
        # 1. Метаданные
        sections.append("=== МЕТАДАННЫЕ ДОКУМЕНТА ===")
        sections.append(f"Имя файла: {parsed_doc.filename}")
        sections.append(f"Страниц: {parsed_doc.page_count}")
        if parsed_doc.metadata:
            for key, value in parsed_doc.metadata.items():
                if value:
                    sections.append(f"{key}: {value}")
        
        # 2. Основная надпись (штамп)
        if parsed_doc.title_block:
            sections.append("\n=== ОСНОВНАЯ НАДПИСЬ ===")
            tb = parsed_doc.title_block
            fields = [
                ("Документ", tb.document_number),
                ("Наименование", tb.product_name),
                ("Материал", tb.material),
                ("Масса", tb.mass),
                ("Масштаб", tb.scale),
                ("Литера", tb.liter),
                ("Разработал", tb.developer),
                ("Проверил", tb.checker),
            ]
            for label, value in fields:
                if value:
                    sections.append(f"{label}: {value}")
        
        # 3. Подписи
        if parsed_doc.signatures:
            sections.append("\n=== ПОДПИСИ ===")
            for sig in parsed_doc.signatures:
                status = "распознано" if sig.confidence > 0.5 else "неясно"
                sections.append(
                    f"{sig.role}: {sig.full_name or 'НЕ РАСПОЗНАНО'} "
                    f"(уверенность: {sig.confidence:.2f}, статус: {status})"
                )
        
        # 4. Текст технических требований
        if parsed_doc.text_content:
            sections.append("\n=== ТЕКСТ ДОКУМЕНТА ===")
            # Группируем текст по страницам для лучшего понимания контекста
            for page_num, text in enumerate(parsed_doc.text_content[:10], 1):  # Ограничение 10 страниц
                if text.strip():
                    sections.append(f"[Стр. {page_num}]: {text[:500]}...")  # Обрезаем длинные тексты
        
        # 5. Таблицы (спецификации и т.д.)
        if parsed_doc.tables:
            sections.append("\n=== ТАБЛИЦЫ ===")
            for idx, table in enumerate(parsed_doc.tables[:5], 1):  # Ограничение 5 таблиц
                sections.append(f"Таблица {idx}:")
                for row in table[:10]:  # Первые 10 строк
                    sections.append(" | ".join(str(cell) for cell in row))
        
        # 6. Предыдущие ошибки (для контекста, чтобы LLM не дублировала)
        if existing_results:
            sections.append("\n=== УЖЕ ВЫЯВЛЕННЫЕ НАРУШЕНИЯ ===")
            errors = [r for r in existing_results if r.status == ValidationStatus.ERROR]
            for err in errors[:10]:  # Первые 10 ошибок
                sections.append(f"- {err.rule_id}: {err.message}")
        
        full_context = "\n".join(sections)
        
        # Ограничение размера контекста (безопасность)
        max_context_length = 8000  # символов
        if len(full_context) > max_context_length:
            logger.warning(f"Context truncated from {len(full_context)} to {max_context_length} chars")
            full_context = full_context[:max_context_length]
        
        return full_context

    @staticmethod
    def convert_to_validation_results(
        llm_results: List[LLMAnalysisResult],
        document_id: int,
    ) -> List[dict]:
        """
        Конвертировать результаты LLM в формат ValidationResult.
        
        Returns:
            Список словарей для создания записей в БД
        """
        validation_results = []
        
        for idx, result in enumerate(llm_results):
            # Маппинг типа нарушения на статус
            status_map = {
                "error": ValidationStatus.ERROR,
                "warning": ValidationStatus.WARNING,
                "info": ValidationStatus.INFO,
            }
            status = status_map.get(result.type.lower(), ValidationStatus.INFO)
            
            validation_results.append({
                "document_id": document_id,
                "rule_id": f"llm_{result.category}_{idx}",
                "rule_name": f"LLM: {result.category}",
                "status": status,
                "message": result.message,
                "details": {
                    "suggestion": result.suggestion,
                    "gost_ref": result.gost_ref,
                    "confidence": result.confidence,
                    "source": "llm",
                },
                "page_ref": None,  # LLM пока не привязывает к странице
                "gost_link": result.gost_ref,
            })
        
        return validation_results
