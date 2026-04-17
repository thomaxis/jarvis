FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY config/ config/
COPY alembic.ini .

RUN useradd -m appuser
USER appuser

ENV PYTHONPATH=/app/..
ENV PYTHONUNBUFFERED=1

EXPOSE 8400

CMD ["python", "-m", "uvicorn", "brain.src.api.server:app", "--host", "0.0.0.0", "--port", "8400"]
