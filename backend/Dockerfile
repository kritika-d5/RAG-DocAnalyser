# Use official Python 3.11-slim as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# fastembed model cache, baked into the image (see below)
ENV FASTEMBED_CACHE_PATH=/models

# Set working directory
WORKDIR /app

# Install system dependencies needed for libraries (e.g. build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker build caching
COPY requirements.txt .

# Install Python dependencies. Embeddings run locally via fastembed (ONNX
# runtime), so there is no torch/transformers stack to install.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model at build time so the first upload after a
# cold start doesn't block on an ~85 MB download.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2')"

# Copy the rest of the backend source code
COPY . .

# Expose the Flask port
EXPOSE 5000

# Start the Flask app with waitress on the host's dynamic PORT (Render etc.)
CMD sh -c "waitress-serve --host=0.0.0.0 --port=${PORT:-5000} --threads=4 app:app"
