FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .
COPY app/ ./app
COPY web/ ./web

CMD ["python", "-m", "bot"]