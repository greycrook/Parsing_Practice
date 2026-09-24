import os
import sys
import json
import time
import sqlite3
import logging
import importlib
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("monitor.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

def load_config(config_file="config.json"):
    if not os.path.exists(config_file):
        logging.error(f"Конфигурационный файл {config_file} не найден!")
        sys.exit(1)
    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)

def init_users_db(users_db_path):
    """Инициализация БД пользователей с тестовыми данными."""
    conn = sqlite3.connect(users_db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_categories (
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        logging.info("Наполнение users.db тестовыми данными...")
        test_users = [
            (1, "Иван Иванов", "ivan@mail.ru"),
            (2, "Петр Петров", "petr@mail.ru"),
            (3, "Анна Сидорова", "anna@mail.ru"),
            (4, "Алексей Смирнов", "alex@mail.ru"),
            (5, "Елена Кузнецова", "elena@mail.ru")
        ]
        cursor.executemany("INSERT INTO users VALUES (?, ?, ?)", test_users)

        test_categories = [
            (1, "Объявления и события"),
            (1, "Наука и инновации"),
            (2, "Образование"),
            (2, "Спорт"),
            (3, "Наука и инновации"),
            (3, "Студенческая жизнь"),
            (4, "Объявления и события"),
            (4, "Образование"),
            (5, "Культура и творчество"),
            (5, "Международная деятельность")
        ]
        cursor.executemany("INSERT INTO user_categories VALUES (?, ?)", test_categories)
        conn.commit()
    conn.close()

def run_parsers(parsers_dir, news_db):
    """Динамический импорт и запуск парсеров."""
    if parsers_dir not in sys.path:
        sys.path.insert(0, parsers_dir)

    for filename in os.listdir(parsers_dir):
        if filename.startswith("parser_") and filename.endswith(".py"):
            module_name = filename[:-3]
            try:
                module = importlib.import_module(module_name)
                importlib.reload(module)  # Перезагрузка для обновления кода при необходимости
                if hasattr(module, "parse"):
                    logging.info(f"Запуск парсера: {module_name}")
                    module.parse(news_db)
                else:
                    logging.warning(f"В модуле {module_name} отсутствует функция parse()")
            except Exception as e:
                logging.error(f"Ошибка при запуске парсера {module_name}: {e}")

def process_matches(config, last_run_time):
    """Сопоставление пользователей и новостей, формирование send_list.txt."""
    news_conn = sqlite3.connect(config["news_db"])
    users_conn = sqlite3.connect(config["users_db"])
    
    news_cursor = news_conn.cursor()
    users_cursor = users_conn.cursor()

    # Извлечение новостей, добавленных с момента последнего цикла
    news_cursor.execute("""
        SELECT id, category FROM news WHERE added_at >= ?
    """, (last_run_time,))
    recent_news = news_cursor.fetchall()

    users_cursor.execute("SELECT id FROM users")
    users = users_cursor.fetchall()

    send_data = {}
    for user in users:
        user_id = user[0]
        users_cursor.execute("SELECT category FROM user_categories WHERE user_id = ?", (user_id,))
        user_cats = set(row[0] for row in users_cursor.fetchall())
        
        matched_news_ids = []
        for news_id, category in recent_news:
            if category in user_cats:
                matched_news_ids.append(str(news_id))
        
        send_data[user_id] = matched_news_ids

    # Запись результатов в файл send_list.txt
    with open(config["output_file"], "w", encoding="utf-8") as f:
        for user_id, news_ids in send_data.items():
            f.write(f"{user_id}: {', '.join(news_ids)}\n")

    logging.info(f"Сформирован список рассылки в файл: {config['output_file']}")

    news_conn.close()
    users_conn.close()

def main():
    config = load_config()
    init_users_db(config["users_db"])

    interval_sec = config.get("interval_minutes", 60) * 60
    logging.info(f"Мониторинговый сервис запущен. Интервал: {config['interval_minutes']} мин.")

    try:
        while True:
            cycle_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logging.info("--- Старт нового цикла парсинга ---")
            
            run_parsers(config["parsers_dir"], config["news_db"])
            process_matches(config, cycle_start_time)

            logging.info(f"Ожидание следующего запуска ({config['interval_minutes']} мин)...")
            time.sleep(interval_sec)

    except KeyboardInterrupt:
        logging.info("Сервис остановлен пользователем (Ctrl+C).")

if __name__ == "__main__":
    main()