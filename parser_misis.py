import sqlite3
import datetime
import requests
from bs4 import BeautifulSoup

UNIVERSITY_NAME = "МИСИС"
NEWS_URL = "https://misis.ru/university/news/"

def parse(db_path="news.db"):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(NEWS_URL, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        response.raise_for_status()
    except Exception as e:
        print(f"[{UNIVERSITY_NAME}] Ошибка при запросе к сайту: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    
    # Поиск блоков новостей МИСИС по классу article__content
    articles = soup.find_all("div", class_=lambda c: c and "article__content" in c)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            link TEXT UNIQUE NOT NULL,
            published_date TEXT NOT NULL,
            category TEXT,
            university TEXT NOT NULL,
            added_at TEXT DEFAULT (datetime('now'))
        )
    """)

    added_count = 0

    for article in articles:
        try:
            # Извлекаем заголовок и ссылку из тега h3 -> a
            h3_tag = article.find("h3")
            if not h3_tag:
                continue

            a_tag = h3_tag.find("a", href=True)
            if not a_tag:
                continue

            title = a_tag.get_text(strip=True)
            if not title:
                continue

            href = a_tag["href"]
            if not href.startswith("http"):
                full_link = "https://misis.ru" + href
            else:
                full_link = href

            # Извлекаем дату из атрибута content тега time (формат: 2026-09-18T17:00:00+03:00)
            time_tag = article.find("time", itemprop="datePublished")
            if time_tag and time_tag.get("content"):
                raw_date = time_tag["content"]
                try:
                    # Обрезаем часовой пояс и форматируем в YYYY-MM-DD HH:MM:SS
                    clean_date = raw_date.split("+")[0].replace("T", " ")
                    dt = datetime.datetime.strptime(clean_date, "%Y-%m-%d %H:%M:%S")
                    pub_date = dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pub_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                pub_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            category = "Наука и инновации"

            cursor.execute("""
                INSERT OR IGNORE INTO news (title, link, published_date, category, university)
                VALUES (?, ?, ?, ?, ?)
            """, (title, full_link, pub_date, category, UNIVERSITY_NAME))

            if cursor.rowcount > 0:
                added_count += 1

        except Exception as e:
            print(f"[{UNIVERSITY_NAME}] Ошибка обработки новости: {e}")
            continue

    conn.commit()
    conn.close()
    print(f"[{UNIVERSITY_NAME}] Парсинг завершён. Добавлено новых новостей: {added_count}")