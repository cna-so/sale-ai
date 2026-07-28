FROM python:3.12-slim

# -----------------------------------------------------------------------
# System packages required by Chromium on Debian bookworm slim.
# We install browser deps manually instead of using `playwright install --with-deps`
# because some font packages (ttf-unifont, ttf-ubuntu-font-family) are NOT
# available in the slim bookworm apt repos and cause build failures.
# -----------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Core network / TLS
    curl \
    wget \
    ca-certificates \
    # Chromium runtime dependencies
    libnss3 \
    libnspr4 \
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
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxext6 \
    libxss1 \
    libxtst6 \
    # Fonts (only ones that exist in bookworm)
    fonts-liberation \
    fonts-noto-color-emoji \
    # Process / misc
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip
RUN pip install --no-cache-dir --timeout 120 --upgrade pip

# -----------------------------------------------------------------------
# Install Python deps in split layers so a timeout on one package
# doesn't invalidate everything already downloaded.
# -----------------------------------------------------------------------
COPY requirements.txt .

# Step 1: Pydantic (compiled Rust wheels - most likely to be slow)
RUN pip install --no-cache-dir --timeout 120 --retries 5 \
    pydantic==2.10.4 \
    pydantic-core==2.27.2 \
    pydantic-settings==2.7.0

# Step 2: FastAPI + Uvicorn
RUN pip install --no-cache-dir --timeout 120 --retries 5 \
    fastapi==0.115.5 \
    "uvicorn[standard]==0.32.1" \
    python-multipart==0.0.12

# Step 3: LangChain / LangGraph / OpenAI
RUN pip install --no-cache-dir --timeout 120 --retries 5 \
    langchain==0.3.14 \
    langchain-openai==0.2.14 \
    langchain-community==0.3.14 \
    langgraph==0.2.60 \
    openai==1.59.3

# Step 4: Qdrant + httpx
RUN pip install --no-cache-dir --timeout 120 --retries 5 \
    qdrant-client==1.12.1 \
    httpx==0.28.1

# Step 5: Playwright Python package (separate layer)
RUN pip install --no-cache-dir --timeout 120 --retries 5 \
    playwright==1.49.0

# Step 6: Remaining utilities
RUN pip install --no-cache-dir --timeout 120 --retries 5 \
    pypdf==5.1.0 \
    python-dotenv==1.0.1 \
    chardet==5.2.0 \
    aiofiles==24.1.0 \
    pytest==8.3.4 \
    pytest-asyncio==0.24.0

# -----------------------------------------------------------------------
# Install Chromium browser WITHOUT --with-deps
# (we already installed all deps manually above)
# This avoids the 'ttf-unifont has no installation candidate' error.
# -----------------------------------------------------------------------
RUN playwright install chromium

# Copy application source
COPY backend/ ./backend/
COPY data/ ./data/

RUN mkdir -p /app/data/uploads /app/data/documents

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
