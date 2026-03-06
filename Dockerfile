FROM python:3.11-slim

WORKDIR /app

# System libraries required by Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser (used by notebooklm-py for Google auth)
RUN playwright install chromium

# Copy application source
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Ensure data directories exist
RUN mkdir -p data/sessions data/temp_uploads

EXPOSE 8000

# 2 workers handles concurrent requests without hammering the NotebookLM quota.
# Timeout 120s gives the NotebookLM browser time to respond.
CMD ["gunicorn", "backend.main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "2", \
     "-b", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
