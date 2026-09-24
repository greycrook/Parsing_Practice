import sqlite3
import datetime
import requests
from bs4 import BeautifulSoup

UNIVERSITY_NAME = "Московский Политех"
NEWS_URL = "https://mospolytech.ru/news/"

# Словарь месяцев для корректного преобразования русскоязычных дат
MONTHS = {
    'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
    'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
    'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'
}

def parse_date(date_container):
    """Парсинг даты из тега с <span> элементами."""
    if not date_container:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    spans = date_container.find_all("span")
    if len(spans) >= 2:
        day = spans[0].get_text(strip=True).zfill(2)
        month_year_raw = spans[1].get_text(" ", strip=True).split()
        
        if len(month_year_raw) >= 2:
            month_str = month_year_raw[0].lower()
            year_str = month_year_raw[1]
            month = MONTHS.get(month_str, "01")
            return f"{year_str}-{month}-{day} 00:00:00"

    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
    
    # Ищем любые новостные карточки Мосполитеха
    articles = soup.find_all("div", class_=lambda c: c and "card-news" in c)

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
            # Извлечение ссылки
            a_tag = article.find("a", class_=lambda c: c and "link" in c) or article.find("a", href=True)
            if not a_tag:
                continue

            href = a_tag["href"]
            if not href.startswith("http"):
                full_link = "https://mospolytech.ru" + href
            else:
                full_link = href

            # Извлечение заголовка
            title_tag = article.find("div", class_=lambda c: c and "title" in c)
            if title_tag:
                title = title_tag.get_text(strip=True)
            else:
                title = a_tag.get_text(strip=True)

            if not title or len(title) < 5:
                continue

            # Извлечение даты
            date_container = article.find("div", class_=lambda c: c and "date" in c)
            pub_date = parse_date(date_container)

            category = "Образование"

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