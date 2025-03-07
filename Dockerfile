FROM nvidia/cuda:12.4.0-devel-ubuntu22.04

ENV DEBIAN_FRONTEND noninteractive
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Установка системных зависимостей
RUN apt-get update && apt-get install --no-install-recommends --no-install-suggests -y \
    python3 \
    python3-pip \
    python3-venv \
    libgl1-mesa-glx \
    && apt clean && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Создание и активация виртуального окружения
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip3 install --no-cache-dir -r requirements.txt

# Копирование проекта
COPY . .

# Создание необходимых директорий
RUN mkdir -p media

# Открываем порт для FastAPI
EXPOSE 8000

# Запуск FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
