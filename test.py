from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Параметры подключения
DB_USER = "postgres"
DB_PASSWORD = "12345678"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "my_database"

# Формируем URL для подключения
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Создаем движок SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_db_connection():
    """Проверка соединения с базой данных перед запуском"""
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT 1")).fetchone()
        db.close()
        if result:
            logger.info("✅ Успешное подключение к базе данных!")
        else:
            logger.error("❌ Подключение есть, но запрос не вернул данные.")
            exit(1)
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД: {e}")
        exit(1)  # Остановка приложения, если нет подключения

def create_test_table():
    """Создает тестовую таблицу"""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS test_table (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                value INTEGER NOT NULL
            )
        """))
        conn.commit()
        logger.info("✅ Таблица test_table создана (если её не было).")

def insert_test_data():
    """Добавляет тестовые данные"""
    with engine.connect() as conn:
        conn.execute(text("INSERT INTO test_table (name, value) VALUES (:name, :value)"), 
                     [{"name": "Test1", "value": 10}, 
                      {"name": "Test2", "value": 20}])
        conn.commit()
        logger.info("✅ Тестовые данные добавлены.")

def get_test_data():
    """Выводит тестовые данные"""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM test_table"))
        rows = result.fetchall()
        for row in rows:
            logger.info(f"📌 Данные: {row}")

if __name__ == "__main__":
    test_db_connection()
    create_test_table()
    insert_test_data()
    get_test_data()
