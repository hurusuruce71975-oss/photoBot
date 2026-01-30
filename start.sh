#!/bin/bash

# Если задан WEBHOOK_URL, значит работаем через вебхук
# Если нет, запускаем поллинг (для локальных тестов)

if [ -z "$PORT" ]; then
    export PORT=3000
fi

echo "Starting server on port $PORT..."
uvicorn main:app --host 0.0.0.0 --port $PORT
