FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git gcc g++ && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir ".[research]"
CMD ["python", "-m", "app.worker"]
