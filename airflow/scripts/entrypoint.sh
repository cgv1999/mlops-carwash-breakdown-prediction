#!/bin/bash
set -e

echo "Starting Airflow entrypoint..."

# Инициализация БД
airflow db init

# Создаем пользователя если нет
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin 2>/dev/null || true

# Запускаем scheduler и webserver
airflow scheduler &
exec airflow webserver -p 8080