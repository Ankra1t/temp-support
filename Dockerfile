FROM python:3.13-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование файлов проекта
COPY main.py .
COPY handlers.py .
COPY database.py .
COPY settings.py .

# Создание файла .env (заполняется пользователем)
RUN touch .env

CMD ["python", "main.py"]
