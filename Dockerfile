# ─────────────────────────────────────────────────
# GridSight SitePlanner — Multi-stage Dockerfile
# ─────────────────────────────────────────────────
FROM python:3.12-slim AS base

LABEL maintainer="jamieson@acidni.net"
LABEL org.opencontainers.image.title="gridsight-site-planner"
LABEL org.opencontainers.image.description="AI-powered site planning and energy estimation"

# Prevent Python from buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ── Dependencies ─────────────────────────────────
FROM base AS deps

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# ── Runtime ──────────────────────────────────────
FROM base AS runtime

# Create non-root user
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Copy installed packages from deps stage
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application source
COPY src/ ./src/

# Set ownership
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 7146

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7146/health')" || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "7146"]
