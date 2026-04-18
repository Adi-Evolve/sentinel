FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY . /app

EXPOSE 5000

CMD ["python", "scripts/run_backend.py"]
