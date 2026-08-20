FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy automation and backend code
COPY automation /app/automation
COPY backend /app/backend

# Upgrade pip, install modules and install matching playwright chromium
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e /app/automation && \
    pip install --no-cache-dir -e /app/backend && \
    playwright install chromium

WORKDIR /app/backend

EXPOSE 8000

ENTRYPOINT ["/app/backend/docker-entrypoint.sh"]
