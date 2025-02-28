# Используем базовый образ с CUDA и Miniconda
FROM nvidia/cuda:12.4.0-devel-ubuntu22.04

# Установка переменных окружения
ENV DEBIAN_FRONTEND noninteractive
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Установка системных зависимостей
RUN apt-get update && apt-get install --no-install-recommends --no-install-suggests -y \
    wget \
    bzip2 \
    build-essential \
    ffmpeg \
    libsm6 \
    libxext6 \
    && apt clean && rm -rf /var/lib/apt/lists/*

# Установка Miniconda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -b -p /opt/conda && \
    rm /tmp/miniconda.sh

# Добавляем Miniconda в PATH
ENV PATH="/opt/conda/bin:$PATH"

# Создание рабочей директории
WORKDIR /app

# Копирование файла с зависимостями
COPY requirements.txt .

# Создание окружения Conda и установка зависимостей
RUN conda create -n myenv python=3.9 && \
    echo "source activate myenv" > ~/.bashrc && \
    /opt/conda/envs/myenv/bin/pip install --no-cache-dir -r requirements.txt

# Копирование проекта
COPY . .

# Создание необходимых директорий
RUN mkdir -p media

# Открываем порт для FastAPI
EXPOSE 8000

# Активация окружения Conda и запуск FastAPI
CMD ["/opt/conda/envs/myenv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]