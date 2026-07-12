# Use an explicit supported Python base image
FROM python:3.11-slim

# Set Python container best practices
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1

# Set deterministic WORKDIR
WORKDIR /app

# Install minimal OS packages if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency metadata before application source for cache efficiency
COPY requirements.txt .

# Install dependencies without pip cache
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download and cache the sentence-transformers model inside the image layer
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Copy application source files
COPY . .

# Expose backend port
EXPOSE 8000

# Start production-style uvicorn without --reload, binding to 0.0.0.0
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
