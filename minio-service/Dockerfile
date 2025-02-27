FROM minio/minio:latest

# Настройка рабочей директории
WORKDIR /minio

# Создание директорий для данных и логов
RUN mkdir -p /data /var/log

# Установка прав доступа
RUN chmod -R 777 /data /var/log

# Экспорт портов
EXPOSE 9000 9001

# Команда запуска
CMD ["server", "/data", "--console-address", ":9001"] 