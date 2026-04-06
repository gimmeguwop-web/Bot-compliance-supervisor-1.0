# ESKD Validator System

Production-ready system for batch validation of engineering documentation against ESKD and GOST standards.

## 🚀 Features

- **PDF Parsing & Analysis**: Extract text, metadata, and structural elements from PDF documents.
- **ESKD/GOST Rule Engine**: YAML-configurable rules for automated compliance checking (GOST 2.104, 2.105, etc.).
- **Computer Vision & OCR**: Detect signature zones, stamps, and extract text using YOLOv8 and EasyOCR.
- **LLM Semantic Analysis**: Identify logical contradictions, terminology inconsistencies, and generate recommendations.
- **Report Generation**: Export detailed reports in `.docx` (Word) and `.xlsx` (Excel) formats.
- **Modern UI**: React-based dashboard with interactive PDF viewer and error overlays.
- **High Performance**: Asynchronous processing with Celery workers, designed for 1000+ files/hour.

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend  │────▶│   FastAPI    │────▶│   PostgreSQL │
│ (React/Mante)│     │   Gateway    │     │   Database   │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │    Redis     │
                    │   Broker     │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Celery Workers│
                    │ (Parser/CV/LLM)│
                    └──────────────┘
```

## 🛠️ Tech Stack

- **Backend**: Python 3.11+, FastAPI, Celery, SQLAlchemy/SQLModel
- **Frontend**: React 18, TypeScript, Mantine UI, Zustand
- **Database**: PostgreSQL 15, Redis 7
- **CV/OCR**: OpenCV, YOLOv8, EasyOCR, Tesseract
- **LLM**: LangChain (OpenAI-compatible API, Ollama support)
- **DevOps**: Docker, docker-compose

## 📋 Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for local frontend development)
- Python 3.11+ (for local backend development)

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd eskd-validator
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings (LLM provider, DB credentials, etc.)
```

### 3. Start Services

```bash
docker-compose up -d
```

Services will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs

### 4. Run Tests

```bash
# Backend tests
docker-compose exec api pytest

# Frontend tests
docker-compose exec frontend npm test
```

## 📁 Project Structure

```
.
├── backend/              # Python backend code
│   ├── app/
│   │   ├── api/          # REST endpoints
│   │   ├── engines/      # Core logic (Parser, Rules, CV, LLM)
│   │   ├── workers/      # Celery tasks
│   │   └── main.py       # App entry point
│   └── pyproject.toml
├── frontend/             # React frontend code
│   ├── src/
│   │   ├── components/   # UI components
│   │   ├── views/        # Pages
│   │   └── store/        # State management
│   └── package.json
├── configs/              # YAML rule profiles & LLM prompts
│   ├── eskd_profiles/
│   └── llm_prompts/
├── docker/               # Dockerfiles
├── docker-compose.yml
└── README.md
```

## ⚙️ Configuration

### Rule Profiles

Edit `configs/eskd_profiles/*.yaml` to customize validation rules:

```yaml
rules:
  - id: "signature_developer"
    type: "ocr_text"
    severity: "error"
    description: "Подпись 'Разработал'"
    params:
      field_name: "Разраб."
      required: true
```

### LLM Settings

Configure LLM provider in `.env`:

```ini
LLM_PROVIDER=ollama
LLM_BASE_URL=http://host.docker.internal:11434/v1
LLM_MODEL_NAME=mistral:7b-instruct-v0.3-q4_K_M
```

## 🧪 Testing

```bash
# Run all tests
pytest backend/tests

# Run with coverage
pytest backend/tests --cov=backend/app

# Lint code
ruff check backend/app
black backend/app
```

## 📄 License

MIT License

## 👥 Contributors

- AI Architect Team
