FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Mount Ombudsman Core (from docker-compose)
ENV PYTHONPATH="/app:/core"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]