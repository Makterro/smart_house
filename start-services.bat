@echo off
echo Starting services...

docker network create minio-network

cd minio-service
docker-compose up -d
cd ..

timeout /t 10 /nobreak

docker-compose up -d

echo Services started successfully!
echo MinIO running on port 9000 (API) and 9001 (Console)
echo Redis running on port 6379