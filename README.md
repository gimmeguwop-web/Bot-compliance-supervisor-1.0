# Система проверки конструкторской документации на соответствие ЕСКД/ГОСТ

Production-ready система для пакетной проверки конструкторской документации (чертежи, спецификации, ТУ, пояснительные записки) на соответствие требованиям ЕСКД и ГОСТ.

## 🚀 Возможности

### Ядро системы
- **Парсинг PDF**: Извлечение текста, метаданных, координат зон с помощью PyMuPDF
- **Rule Engine**: Детерминированные проверки по YAML-профилям ГОСТ (2.104, 2.105, 2.109, 2.106)
- **CV/OCR модуль**: Детекция зон подписей (YOLOv8 + OpenCV), распознавание ФИО (EasyOCR)
- **LLM-анализатор**: Семантическая проверка техтребований, выявление противоречий, рекомендации
- **Экспорт отчётов**: Генерация .docx (структурированный отчёт) и .xlsx (матричный отчёт)

### Производительность
- До **1000 файлов/час** благодаря асинхронному пулу Celery-воркеров
- Graceful degradation при ошибках OCR/LLM
- Кэширование моделей и промежуточных результатов
- Ограничение памяти на чанки PDF

### Безопасность
- Sandbox-парсинг PDF (защита от PDF-бомб)
- Валидация MIME-типов и размеров файлов
- Rate-limiting для LLM/OCR запросов
- Ролевая модель (admin, operator, viewer)

## 🏗️ Архитектура

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Frontend  │────▶│  FastAPI GW  │────▶│  Celery Workers │
│ React+Mantine│◀────│  WebSocket   │◀────│  Pool (N instances)│
└─────────────┘     └──────────────┘     └─────────────────┘
                           │                      │
                           ▼                      ▼
                    ┌──────────────┐     ┌─────────────────┐
                    │  PostgreSQL  │     │     Redis       │
                    │  (Metadata)  │     │  (Broker/Cache) │
                    └──────────────┘     └─────────────────┘
```

### Технологический стек
- **Backend**: Python 3.11+, FastAPI, Celery, SQLAlchemy/SQLModel
- **Frontend**: React 18 + TypeScript, Mantine UI, Zustand, WebSocket
- **БД**: PostgreSQL 15+, Redis 7+
- **PDF/CV**: PyMuPDF, pdfplumber, OpenCV, YOLOv8n, EasyOCR
- **LLM**: LangChain, OpenAI-compatible API (Ollama/vLLM/OpenAI)
- **DevOps**: Docker, docker-compose, pytest, GitHub Actions

## 📦 Быстрый старт (локально)

### Предварительные требования
- Docker 24+ и Docker Compose 2.20+
- 8GB+ RAM (для LLM и OCR моделей)
- 20GB свободного места

### 1. Клонирование и настройка
```bash
cd /workspace
cp .env.example .env
# Отредактируйте .env при необходимости (LLM_PROVIDER, пароли и т.д.)
```

### 2. Запуск через docker-compose
```bash
docker-compose up -d
```

Компоненты:
- `api`: FastAPI сервер (порт 8000)
- `worker`: Celery воркер (масштабируется горизонтально)
- `frontend`: React приложение (порт 3000)
- `db`: PostgreSQL
- `redis`: Redis broker
- `ollama`: Локальная LLM (опционально, порт 11434)

### 3. Проверка статуса
```bash
docker-compose ps
# Все сервисы должны быть в состоянии "Up"
```

### 4. Открыть веб-интерфейс
```
http://localhost:3000
```

API документация доступна по адресу: `http://localhost:8000/docs`

## 🔧 Конфигурация

### Переменные окружения (.env)

| Переменная | Описание | Пример |
|------------|----------|--------|
| `APP_ENV` | Режим работы | `development` / `production` |
| `SECRET_KEY` | Ключ шифрования сессий | `your-secret-key` |
| `DATABASE_URL` | Строка подключения к БД | `postgresql://user:pass@db:5432/eskd_db` |
| `REDIS_URL` | URL Redis брокера | `redis://redis:6379/0` |
| `LLM_PROVIDER` | Провайдер LLM | `ollama` / `openai` / `none` |
| `LLM_BASE_URL` | URL LLM API | `http://ollama:11434/v1` |
| `LLM_MODEL_NAME` | Модель для анализа | `mistral:7b-instruct-v0.3-q4_K_M` |
| `OCR_LANG` | Языки OCR | `ru,en` |
| `YOLO_MODEL_PATH` | Путь к модели детекции подписей | `models/yolov8n-signatures.pt` |

### Профили проверок (configs/eskd_profiles/)

Пример профиля `gost_2.105_basic.yaml`:
```yaml
profile_id: "gost_2.105_basic"
name: "ГОСТ 2.105-2018: Текстовые документы"
rules:
  - id: "title_presence"
    type: "text_exists"
    description: "Наличие заголовка документа"
    params:
      min_length: 10
      required: true
  
  - id: "page_numbering"
    type: "metadata_check"
    description: "Сквозная нумерация страниц"
    params:
      check_sequence: true
```

## 📡 API Endpoints

### Загрузка документа
```bash
POST /api/v1/documents/upload
Content-Type: multipart/form-data

FormData:
  - file: <PDF файл>
  - profile_id: "gost_2.105_basic"
  
Response:
{
  "task_id": 123,
  "document_id": 456,
  "status": "pending"
}
```

### Статус задачи
```bash
GET /api/v1/tasks/{task_id}

Response:
{
  "id": 123,
  "status": "processing",
  "progress": 65,
  "stage": "vision",
  "message": "Поиск подписей и штампов..."
}
```

### Результаты проверки
```bash
GET /api/v1/tasks/{task_id}/results

Response:
{
  "task_id": 123,
  "status": "completed",
  "results": [
    {
      "rule_id": "title_presence",
      "status": "pass",
      "description": "Наличие заголовка документа",
      "page_ref": 1
    },
    {
      "rule_id": "signature_developer",
      "status": "error",
      "description": "Подпись 'Разработал' не найдена",
      "page_ref": 1,
      "gost_link": "ГОСТ 2.104-2006, п.5.2"
    }
  ],
  "reports": {
    "docx": "/app/data/reports/report_123.docx",
    "xlsx": "/app/data/reports/matrix_123.xlsx"
  }
}
```

### Скачивание отчёта
```bash
GET /api/v1/reports/{task_id}/docx
GET /api/v1/reports/{task_id}/xlsx
```

## 🎯 WebSocket для live-статуса

Подписка на обновления задачи:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/tasks');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'subscribe',
    task_id: 123
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'update') {
    console.log(`Progress: ${data.data.progress}% - ${data.data.message}`);
  }
};
```

## 🧪 Тестирование

### Запуск тестов
```bash
# Backend tests
docker-compose exec api pytest

# Frontend tests
docker-compose exec frontend npm run test

# Integration tests
docker-compose exec api pytest tests/integration/
```

### Эталонные файлы
Тестовые PDF находятся в `/workspace/backend/tests/fixtures/`:
- `valid_drawing_a4.pdf` - корректный чертёж А4
- `missing_signature.pdf` - документ без подписи
- `invalid_format.pdf` - документ с нарушениями форматирования

## 📊 Мониторинг и логи

### Просмотр логов
```bash
# Все сервисы
docker-compose logs -f

# Только API
docker-compose logs -f api

# Воркеры
docker-compose logs -f worker
```

### Метрики производительности
- Время обработки одного документа: ~30-60 сек (зависит от объёма)
- Пропускная способность: до 1000 файлов/час при 10 воркерах
- Потребление памяти: ~500MB на воркер + ~2GB на LLM модель

## ☁️ Развёртывание в облаке

### Подготовка к продакшену
1. Замените локальные тома на управляемые БД (RDS, Cloud SQL)
2. Настройте S3-compatible хранилище для файлов
3. Увеличьте пул воркеров: `docker-compose scale worker=10`
4. Включите HTTPS через reverse proxy (nginx/traefik)
5. Настройте мониторинг (Prometheus + Grafana)

## 🛠️ Расширение функциональности

### Добавление нового правила ГОСТ
1. Создайте YAML-файл в `/configs/eskd_profiles/`
2. Реализуйте логику проверки в `/backend/app/engines/rules/checks/`
3. Зарегистрируйте правило в `rule_engine.py`

### Интеграция новой LLM модели
1. Добавьте провайдер в `/backend/app/engines/llm/providers/`
2. Обновите конфиг `.env` (LLM_BASE_URL, LLM_MODEL_NAME)
3. Протестируйте через API

## 📝 Лицензия

Система разработана для внутреннего использования. Все права защищены.

## 👥 Поддержка

Вопросы и предложения направляйте на внутреннюю почту команды разработки.

---
**Версия**: 1.0.0  
**Дата обновления**: 2025-01-01
