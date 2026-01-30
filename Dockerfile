FROM python:3.10-slim

WORKDIR /app

# Устанавливаем зависимости системы
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы проекта
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создаем папку для логов или временных файлов, если нужно
# RUN mkdir -p temp

# Права на выполнение скрипта запуска
RUN chmod +x start.sh

# Переменные окружения по умолчанию (можно переопределить при запуске)
ENV PORT=3000

# Команда запуска
CMD ["./start.sh"]

