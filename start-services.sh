#!/bin/bash

# Создание сети, если она не существует
docker network create minio-network || true

# Запуск MinIO
cd minio-service
docker-compose up -d
cd ..

# Ожидание запуска MinIO
echo "Waiting for MinIO to start..."
sleep 10

# Запуск Redis
docker-compose up -d

echo "Services started successfully!"
echo "MinIO running on port 9000 (API) and 9001 (Console)"
echo "Redis running on port 6379" 