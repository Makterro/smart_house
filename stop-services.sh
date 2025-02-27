#!/bin/bash

# Остановка Redis
docker-compose down

# Остановка MinIO
cd minio-service
docker-compose down
cd ..

# Удаление сети
docker network rm minio-network || true

echo "Services stopped successfully!" 