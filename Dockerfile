FROM python:3.13-slim

WORKDIR /app

# Install system deps for ML libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .
COPY lib/ lib/
COPY models/ models/
COPY data/ data/

ENV PORT=8000
EXPOSE 8000

CMD gunicorn server:app --bind 0.0.0.0:$PORT --timeout 600 --workers 1 --worker-class gthread --threads 2
