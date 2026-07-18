# Use official Python 3.11-slim as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Store Hugging Face models in a distinct system-wide cache directory
ENV HF_HOME=/hf_cache

# Set working directory
WORKDIR /app

# Install system dependencies needed for libraries (e.g. build tools, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker build caching
COPY requirements.txt .

# Install Python dependencies. Embeddings are served by the HuggingFace
# Inference API, so there is no heavy ML stack (torch/transformers) to install
# and no model to pre-bake.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend source code
COPY . .

# Expose the Flask port
EXPOSE 5000

# Start the Flask app with waitress on Render's dynamic PORT
CMD sh -c "waitress-serve --host=0.0.0.0 --port=${PORT:-5000} app:app"
