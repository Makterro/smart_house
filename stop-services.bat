@echo off
echo Stopping services...

docker-compose down

cd minio-service
docker-compose down
cd ..

docker network rm minio-network

echo Services stopped successfully!