import sqlite3
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import schedule

BASE_URL = "https://mai.ru"
CATEGORY_URL = f"{BASE_URL}/press/news/index.php?SECTION_ID=science"
CATEGORY_NAME = "Наука"
DB_NAME = "mai_news.db"
CHECK_INTERVAL_MINUTES = 10  # Чек новых новостей каждые 10 минут

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            publication_date TEXT,
            link TEXT UNIQUE NOT NULL,
            detection_time TEXT NOT NULL,
            category TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def fetch_latest_news():
    try:
        response = requests.get(CATEGORY_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    card = soup.select_one(".card-pinned, .card")
    if not card:
        return None

    title_tag = card.select_one("h5")
    if not title_tag:
        return None
    title = title_tag.get_text(strip=True)

    link_tag = card.find("a", href=True)
    href = link_tag["href"] if link_tag else ""
    link = f"{BASE_URL}{href}" if href.startswith("/") else href

    date_tag = card.select_one(".badge") or card.select_one(".card-pinned-top-end")
    pub_date = date_tag.get_text(strip=True) if date_tag else "Дата не указана"

    return {
        "title": title,
        "publication_date": pub_date,
        "link": link,
        "category": CATEGORY_NAME
    }


def check_for_updates():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    news = fetch_latest_news()
    if not news:
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO news (title, publication_date, link, detection_time, category)
            VALUES (?, ?, ?, ?, ?)
        ''', (news["title"], news["publication_date"], news["link"], now_str, news["category"]))
        conn.commit()
        print(f"[{now_str}] Новая новость: {news['title']}")
    except sqlite3.IntegrityError:
        print(f"[{now_str}] Обновлений нет.")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    check_for_updates()
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(check_for_updates)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        pass