FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY apps ./apps
COPY data ./data
COPY docs ./docs
COPY scripts ./scripts

RUN pip install --no-cache-dir .
RUN python scripts/build_microsite.py

CMD ["sh", "-c", "python -m uvicorn apps.site.server:app --host 0.0.0.0 --port ${PORT:-8080}"]
