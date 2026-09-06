FROM python:3.12-slim

WORKDIR /app

# Build tooling needed by some scientific wheels
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Copy package metadata first
COPY pyproject.toml ./

# IMPORTANT: pip install . needs the app package to exist
COPY app ./app

# Install the full stack (ML + PII extras) for the running service.
# Extras are explicit so a failure here is loud, not a silently degraded image.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ".[ml,pii]"

# spaCy model for Presidio's NER-based PII detection
RUN python -m spacy download en_core_web_sm

# Copy remaining backend files
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]