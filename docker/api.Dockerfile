FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY apps ./apps
COPY scripts ./scripts

RUN pip install --no-cache-dir .

CMD ["python", "-m", "research_os.api_server"]
