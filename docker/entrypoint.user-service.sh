#!/bin/bash
# (7�/�,

set -e

echo "Starting User Service..."

# I�pn�1�
echo "Waiting for database..."
while ! nc -z postgres 5432; do
    echo "Database is unavailable - sleeping"
    sleep 1
done
echo "Database is up!"

# I�Redis1�
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
    echo "Redis is unavailable - sleeping"
    sleep 1
done
echo "Redis is up!"

# �Lpn���
echo "Running database migrations..."
alembic upgrade head

# ����/&�
if [ $? -eq 0 ]; then
    echo "Database migrations completed successfully"
else
    echo "Database migrations failed"
    exit 1
fi

# /��(
echo "Starting application..."
exec "$@"
