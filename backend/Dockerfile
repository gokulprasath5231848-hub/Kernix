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

# Which optional extras to install. Default is core-only so the image fits on
# small/free hosts (e.g. Render free, 512 MB) — the app degrades gracefully:
# lexical embeddings instead of sentence-transformers, regex instead of Presidio.
# For a full-featured image on a larger host, build with:
#   --build-arg PIP_EXTRAS=".[ml,pii]"
ARG PIP_EXTRAS="."
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir "${PIP_EXTRAS}"

# spaCy's NER model is only useful when Presidio (the pii extra) is installed.
RUN python -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('presidio_analyzer') else 1)" \
    && python -m spacy download en_core_web_sm \
    || echo "Presidio not installed; skipping spaCy model download (regex PII fallback)."

# Copy remaining backend files
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]