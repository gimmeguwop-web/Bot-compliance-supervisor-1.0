from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from langchain.schema import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LLMAnalysisResult(BaseModel):
    """Результат анализа LLM."""

    type: str = Field(..., description="Тип нарушения: error, warning, info")
    category: str = Field(..., description="Категория: semantic, contradiction, recommendation")
    message: str = Field(..., description="Описание проблемы")
    gost_ref: Optional[str] = Field(None, description="Ссылка на ГОСТ")
    suggestion: str = Field(..., description="Рекомендация по исправлению")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Уверенность модели")


class LLMProvider(ABC):
    """Абстрактный интерфейс для LLM-провайдера."""

    @abstractmethod
    async def analyze(self, context: str) -> List[LLMAnalysisResult]:
        """Выполнить семантический анализ контекста."""
        pass


class OpenAICompatibleProvider(LLMProvider):
    """Провайдер для OpenAI-compatible API (включая Ollama, vLLM)."""

    def __init__(
        self,
        base_url: str,
        model_name: str,
        api_key: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.1,
    ):
        self.base_url = base_url
        self.model_name = model_name
        self.api_key = api_key or "ollama"  # Ollama не требует ключа
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # Ленивая инициализация клиента
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from langchain_openai import ChatOpenAI
                self._client = ChatOpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key,
                    model=self.model_name,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )
            except ImportError:
                logger.error("langchain-openai not installed. Install with: pip install langchain-openai")
                raise
        return self._client

    async def analyze(self, context: str) -> List[LLMAnalysisResult]:
        """Выполнить анализ через LLM."""
        try:
            # Загрузка промпта
            prompt_template = self._load_prompt_template()
            formatted_prompt = prompt_template.replace("{{context}}", context)

            messages = [
                SystemMessage(content="Ты — эксперт по ЕСКД и ГОСТ. Отвечай строго в формате JSON."),
                HumanMessage(content=formatted_prompt),
            ]

            response = await self.client.ainvoke(messages)
            content = response.content.strip()

            # Парсинг JSON ответа
            # Иногда модели оборачивают JSON в markdown блоки
            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0].strip()
            elif content.startswith("```"):
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)
            
            # Валидация и конвертация в модели
            results = []
            for item in data:
                try:
                    result = LLMAnalysisResult(**item)
                    results.append(result)
                except Exception as e:
                    logger.warning(f"Failed to parse LLM result item: {e}, item: {item}")
                    continue
            
            return results

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            # Graceful degradation: возвращаем пустой список вместо падения
            return []

    def _load_prompt_template(self) -> str:
        """Загрузить шаблон промпта из файла."""
        import os
        prompt_path = os.path.join(os.path.dirname(__file__), "../../../configs/llm_prompts/semantic_analysis.txt")
        
        # Попытка загрузки из разных путей
        possible_paths = [
            prompt_path,
            "/workspace/configs/llm_prompts/semantic_analysis.txt",
            "configs/llm_prompts/semantic_analysis.txt",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
        
        # Fallback промпт если файл не найден
        logger.warning("Prompt template not found, using fallback")
        return """
Ты — эксперт по ЕСКД. Проанализируй данные и найди ошибки.
Верни JSON массив с полями: type, category, message, gost_ref, suggestion, confidence.
Контекст: {{context}}
"""


class MockLLMProvider(LLMProvider):
    """Mock-провайдер для тестирования без реального LLM."""

    async def analyze(self, context: str) -> List[LLMAnalysisResult]:
        """Возвращает тестовые результаты."""
        logger.info("Using MockLLMProvider for testing")
        return [
            LLMAnalysisResult(
                type="warning",
                category="recommendation",
                message="Тестовое предупреждение от Mock LLM",
                gost_ref="ГОСТ 2.104-2006",
                suggestion="Проверить вручную",
                confidence=0.95,
            )
        ]


def get_llm_provider(
    provider_type: str,
    base_url: str,
    model_name: str,
    api_key: Optional[str] = None,
) -> LLMProvider:
    """Фабрика для создания LLM-провайдера."""
    
    if provider_type == "mock":
        return MockLLMProvider()
    elif provider_type in ["openai", "ollama", "vllm"]:
        return OpenAICompatibleProvider(
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
        )
    else:
        logger.warning(f"Unknown LLM provider type: {provider_type}, falling back to mock")
        return MockLLMProvider()
