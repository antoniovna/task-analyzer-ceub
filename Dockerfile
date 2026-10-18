# Empacotamento do TaskAnalyzer — contrato na seção 4.5 de specs/task_analyzer_spec.md.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

RUN useradd --create-home --uid 1000 analyzer

WORKDIR /app

# Dependências em camada própria: só são reinstaladas quando requirements.txt muda.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=analyzer:analyzer src/ src/
COPY --chown=analyzer:analyzer tests/ tests/
RUN chown analyzer:analyzer /app

USER analyzer

CMD ["pytest", "tests/test_harness.py", "-v", \
     "--cov=src", "--cov-report=term-missing", "--cov-fail-under=90"]
