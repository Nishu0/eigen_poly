FROM python:3.13-slim

WORKDIR /app

# Install system deps for asyncpg and web3
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python deps
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy app code
COPY . .

# Expose port
EXPOSE ${PORT:-8000}

# Start server
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}
