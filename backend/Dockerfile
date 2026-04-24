FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN sed -i 's/\r$//' docker-entrypoint.sh && chmod +x docker-entrypoint.sh

# Railway sets PORT; default 8000 for local docker run.
EXPOSE 8000
ENV PORT=8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
# Default: uvicorn on $PORT. docker-compose overrides with explicit command (e.g. --reload).
CMD []
