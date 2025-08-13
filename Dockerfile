
# Minimal Dockerfile for Telegram PA-Bot
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expect TELEGRAM_TOKEN and DATA_PATH at runtime
CMD ["python", "bot.py"]
