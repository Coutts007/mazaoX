FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first so this layer is cached until requirements.txt changes.
COPY requirements.txt .
RUN pip install --default-timeout=120 --retries 10 -r requirements.txt

RUN useradd --create-home --uid 1000 mazaox && mkdir -p /app/media && chown -R mazaox /app
COPY --chown=mazaox . .
RUN chmod +x docker-entrypoint.sh

USER mazaox
ENV MEDIA_ROOT=/app/media
EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
