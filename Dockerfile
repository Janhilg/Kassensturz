FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV KASSENSTURZ_MODE=production

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py config.py ./
COPY core ./core
COPY static ./static
COPY templates ./templates

RUN mkdir -p /app/data /app/logs \
    && useradd --create-home --shell /usr/sbin/nologin kassensturz \
    && chown -R kassensturz:kassensturz /app

USER kassensturz

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
