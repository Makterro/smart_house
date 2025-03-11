# Video Aggression Detection System

Система анализа видео для детекции агрессивных действий через построение скелетов с использованием YOLOv8 Pose, FastAPI и Celery.

## 📌 Основные возможности

- **Автоматическая обработка видео** при загрузке в MinIO bucket
- **Построение скелетов** с помощью YOLOv8 Pose модель
- **Детекция агрессивных действий** на основе анализа ключевых точек
- **Распределенная обработка** через Celery workers
- **Интеграция с MinIO** для хранения видео и метаданных
- **GPU acceleration** поддержка (NVIDIA)

## 🛠 Технологический стек

- **Backend**: FastAPI
- **Computer Vision**: YOLOv8 Pose
- **Task Queue**: Celery + Redis
- **Storage**: MinIO
- **GPU Support**: CUDA, NVIDIA Docker
- **Containerization**: Docker

## 📦 Требования

- Docker version 27.3.1, build ce12230
- NVIDIA GPU (рекомендуется)
- NVIDIA Container Toolkit

## 🚀 Быстрый старт

docker compose up --build

## 📂 Структура проекта

```text
Copy
├── app
│   ├── db              # Database models and sessions
│   ├── schemas         # Pydantic models
│   ├── services        # Business logic
│   ├── utils           # Helper functions
│   └── worker.py       # Celery tasks
├── media               # Processed videos
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 🧩 Архитектура системы

```text
+-------------+       +------------+       +---------+       +-------------+
|   MinIO     |       |   FastAPI  |       |  Redis  |       |  Celery     |
| (Video      +------>+ (Webhook   +------>+ (Broker +------>+ Workers     |
| Storage)    |       |  Handler)  |       |         |       | (GPU)       |
+-------------+       +------------+       +---------+       +------+------+
                                                                     |
                                                                     v
                                                               +-----+-----+
                                                               | Postgres  |
                                                               | Database  |
                                                               +-----------+
```