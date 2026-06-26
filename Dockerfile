# MUSTAFA MIXING — Dockerfile
FROM python:3.11-slim

LABEL maintainer="Mustafa Kamal <mustafaprotools2011@github>"
LABEL description="MUSTAFA MIXING — Global Music Credits Intelligence Platform"

# Install system dependencies: SQLite, tini (for proper signal handling)
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r mustafa && useradd -r -g mustafa -d /app -s /sbin/nologin mustafa

# Set working directory
WORKDIR /app

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for backups and static
RUN mkdir -p backups static && chown -R mustafa:mustafa /app

# Switch to non-root user
USER mustafa

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/')" || exit 1

# Use tini to properly handle signals (SIGTERM, etc.)
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command — run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
