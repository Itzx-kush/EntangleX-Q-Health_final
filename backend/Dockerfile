FROM python:3.11.16-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements*.txt /app/
RUN python -m pip install --upgrade pip && python -m pip install -r /app/requirements.txt
RUN useradd --uid 10001 --create-home qhealth && mkdir -p /runtime/data/datasets /runtime/models /runtime/experiments && chown -R qhealth:qhealth /runtime /app
COPY --chown=qhealth:qhealth app /app/app
USER qhealth
ENV QHEALTH_STORAGE_ROOT=/runtime
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
