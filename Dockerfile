FROM python:3.12-slim

# System deps for Playwright + general build
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    gnupg \
    ca-certificates \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip first
RUN pip install --no-cache-dir --timeout 120 --upgrade pip

# -----------------------------------------------------------------------
# Install heavy / compiled packages first in a separate layer.
# Split so a timeout on one package doesn't re-download everything.
# -----------------------------------------------------------------------
COPY requirements.txt .

# Step 1: core compiled wheels (most likely to time out - install alone)
RUN pip install --no-cache-dir --timeout 120 --retries 5 \
    pydantic==2.10.4 \
    pydantic-core==2.27.2 \
    pydantic-settings==2.7.0

# Step 2: FastAPI + Uvicorn
RUN pip install --no-cache-dir --timeout 120 --retries 5 \
    fastapi==0.115.5 \
    uvicorn[standard]==0.32.1 \
    python-multipart==0.0.12

# Step 3: LLM / AI stack
RUN pip install --no-cache-dir --timeout 120 --retries 5 \
    langchain==0.3.14 \
    langchain-openai==0.2.14 \
    langchain-community==0.3.14 \
    langgraph==0.2.60 \
    openai==1.59.3

# Step 4: Vector store + HTTP
RUN pip install --no-cache-dir --timeout 120 --retries 5 \
    qdrant-client==1.12.1 \
    httpx==0.28.1

# Step 5: Playwright (large download - separate layer for cache)
RUN pip install --no-cache-dir --timeout 120 --retries 5 \
    playwright==1.49.0

# Step 6: Remaining deps
RUN pip install --no-cache-dir --timeout 120 --retries 5 \
    pypdf==5.1.0 \
    python-dotenv==1.0.1 \
    chardet==5.2.0 \
    aiofiles==24.1.0 \
    pytest==8.3.4 \
    pytest-asyncio==0.24.0

# Install Playwright Chromium browser (separate layer - ~170MB)
# This layer is cached independently so network interruptions only re-download the browser
RUN playwright install chromium --with-deps

# Copy application source
COPY backend/ ./backend/
COPY data/ ./data/

# Create data dirs
RUN mkdir -p /app/data/uploads /app/data/documents

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
