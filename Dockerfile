# 1. Base Image (Small & Fast)
FROM python:3.10-slim

# 2. Environment Variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 3. Set Work Directory
WORKDIR /app

# 4. Install System Dependencies (Required for some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    musl-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 5. Install Python Dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# 6. Copy Application Code
COPY . .

# 7. Create a Non-Root User (Security Best Practice)
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# 8. Command to Run (Uses the $PORT variable)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}