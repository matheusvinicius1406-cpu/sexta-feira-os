FROM python:3.12-slim

WORKDIR /app

# Lean image: no compilers needed (pure-python deps + numpy wheels).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persistent brain data lives here (mounted from the host in compose).
RUN mkdir -p /data && useradd -m sexta && chown -R sexta /app /data
USER sexta

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
