import sqlite3
import datetime
import requests
from bs4 import BeautifulSoup

UNIVERSITY_NAME = "МЭИ"
NEWS_URL = "https://mpei.ru/News/Pages/default.aspx"

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
    
    # Поиск всех блоков новостей по классу newsitem
    news_items = soup.find_all("div", class_=lambda c: c and "newsitem" in c)

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

    for item in news_items:
        try:
            # Извлекаем заголовок и ссылку из контейнера newstitle
            title_container = item.find("div", class_=lambda c: c and "newstitle" in c)
            if not title_container:
                continue
                
            a_tag = title_container.find("a", href=True)
            if not a_tag:
                continue

            title = a_tag.get_text(strip=True)
            if not title:
                continue

            href = a_tag["href"]
            if not href.startswith("http"):
                full_link = "https://mpei.ru" + href
            else:
                full_link = href

            # Извлекаем дату из контейнера newsdate-list
            date_container = item.find("div", class_=lambda c: c and "newsdate-list" in c)
            if date_container:
                raw_date = date_container.get_text(strip=True)
                # Переводим из DD.MM.YYYY в YYYY-MM-DD HH:MM:SS согласно ТЗ
                try:
                    dt = datetime.datetime.strptime(raw_date, "%d.%m.%Y")
                    pub_date = dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pub_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                pub_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            category = "Объявления и события"

            cursor.execute("""
                INSERT OR IGNORE INTO news (title, link, published_date, category, university)
                VALUES (?, ?, ?, ?, ?)
            """, (title, full_link, pub_date, category, UNIVERSITY_NAME))
            
            if cursor.rowcount > 0:
                added_count += 1

        except Exception as e:
            print(f"[{UNIVERSITY_NAME}] Ошибка обработки элементы новости: {e}")
            continue

    conn.commit()
    conn.close()
    print(f"[{UNIVERSITY_NAME}] Парсинг завершён. Добавлено новых новостей: {added_count}")