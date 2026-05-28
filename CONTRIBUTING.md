# Contributing to PMRS

Thank you for your interest in contributing to PMRS (Protocol Mining and Reverse-engineering System)! This document provides guidelines for contributing to the ICS protocol vulnerability fuzzing platform.

## Getting Started

### Prerequisites

- Python >= 3.10
- Node.js >= 18 (for frontend)
- PostgreSQL >= 15
- Redis >= 7
- AFL++ (optional, for fuzzing features)

### Development Setup

```bash
# Clone the repository
git clone <repo-url>
cd pmrs

# ---- Backend ----
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install pytest pytest-cov httpx
cp .env.example .env  # Edit with your API keys

# ---- Frontend ----
cd ../frontend
npm install

# ---- Database (Docker) ----
docker run -d --name pmrs-postgres \
  -e POSTGRES_DB=pmrs -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 postgres:15-alpine

docker run -d --name pmrs-redis -p 6379:6379 redis:7-alpine
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Follow PEP 8 for Python code
- Use TypeScript for frontend code
- Add docstrings to all public functions and classes
- Keep API routes RESTful and well-documented

### 3. Run Tests

```bash
# Run all backend tests
cd backend
PYTHONPATH=. pytest ../tests/ -v

# Run with coverage
PYTHONPATH=. pytest ../tests/ -v --cov=. --cov-report=term-missing

# Run specific test file
PYTHONPATH=. pytest ../tests/test_protocols.py -v

# Run frontend tests
cd frontend
npm run test
```

### 4. Lint Your Code

```bash
# Python
ruff check backend/ --ignore E501,W503

# TypeScript/Vue
cd frontend && npm run lint
```

### 5. Test with Docker Compose

```bash
docker-compose up -d
# Verify: http://localhost:3000 (frontend), http://localhost:8000/docs (API)
```

### 6. Commit and Push

```bash
git add .
git commit -m "feat: description of your change"
git push origin feature/your-feature-name
```

### 7. Open a Pull Request

- Describe the purpose of the PR
- Reference any related issues
- Include screenshots for UI changes
- Ensure CI passes before requesting review

## Code Structure

```
pmrs/
  backend/
    api/              # FastAPI route handlers
    core/             # Config, database, security, logging
    models/           # SQLAlchemy ORM models
    schemas/          # Pydantic request/response schemas
    services/         # Business logic (CVSS, LLM, scanner)
    protocols/        # ICS protocol implementations
    fuzzers/          # AFL++ wrapper
    main.py           # FastAPI application entry point
  frontend/
    src/
      pages/          # Vue page components
      api/            # API client modules
      router/         # Vue Router config
  tests/              # Test suite
  docker-compose.yml  # Full-stack deployment
```

## Adding a New ICS Protocol

1. Create a new file in `backend/protocols/` (e.g., `profinet.py`)
2. Subclass `ProtocolBase` and implement `parse()`, `build()`, `validate()`
3. Register with `ProtocolRegistry.register("profinet", ProfinetProtocol)`
4. Write tests in `tests/test_protocols.py`
5. Update `SUPPORTED_PROTOCOLS` in `core/config.py`

## Adding a New API Endpoint

1. Create or edit a router in `backend/api/`
2. Define Pydantic schemas in `backend/schemas/`
3. Implement business logic in `backend/services/`
4. Register the router in `backend/api/__init__.py`
5. Write integration tests using `httpx.AsyncClient`

## Testing Guidelines

- Every new module should have corresponding tests in `tests/`
- Tests should be runnable without external services (mock DB/Redis)
- Use `pytest.fixture` for shared setup
- Aim for >80% coverage on new code

### Test Categories

| File | Covers |
|------|--------|
| `test_smoke.py` | Import validation for all modules |
| `test_protocols.py` | ModbusTCP, DNP3, IEC61850 protocol parsing |
| `test_cvss.py` | CVSS 3.1 calculator and severity classification |

## Reporting Issues

- Use GitHub Issues
- Include a minimal reproducible example
- Specify your environment (OS, Python version, Docker version)
- For protocol parsing bugs, include the raw packet hex dump

## Security

- Never commit API keys or credentials
- Use environment variables for secrets
- Report security vulnerabilities privately to the maintainers

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
