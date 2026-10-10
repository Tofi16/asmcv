FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

COPY . ./

EXPOSE 8080
CMD ["sh", "-c", "exec gunicorn --workers 2 --bind 0.0.0.0:${PORT:-8080} app:app"]