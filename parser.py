import csv
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt

# 1. Настройки парсинга
# Выбрана категория "Наука"
BASE_URL = "https://mai.ru"
CATEGORY_URL = f"{BASE_URL}/press/news/index.php?SECTION_ID=science"
CSV_FILENAME = "mai_science_news.csv"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

news_data = []
page = 1

print("Начинаем сбор новостей...")

# 2. Сбор всех новостей по страницам пагинации
MAX_PAGES = 30  

while page <= MAX_PAGES:
    url = f"{CATEGORY_URL}&PAGEN_1={page}"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        break

    soup = BeautifulSoup(response.text, "html.parser")
    
    # Ищем карточки новостей
    cards = soup.select(".card-pinned, .card")
    
    
    if not cards:
        break

    parsed_on_page = 0
    for card in cards:
        title_tag = card.select_one("h5")
        if not title_tag:
            continue

        news_title = title_tag.get_text(strip=True)

        # Поиск ссылки
        link_tag = card.find("a", href=True)
        href = link_tag["href"] if link_tag else ""
        news_link = f"{BASE_URL}{href}" if href.startswith("/") else href

        # Поиск даты
        date_tag = card.select_one(".badge") or card.select_one(".card-pinned-top-end")
        news_date = date_tag.get_text(strip=True) if date_tag else None

        if news_title and news_date:
            news_data.append([news_date, news_title, news_link])
            parsed_on_page += 1

    # Прекращаем цикл, если новости перестали находиться
    if parsed_on_page == 0:
        break

    print(f"Собрано со страницы {page}: {parsed_on_page} новостей")
    page += 1

# 3. Сохранение данных в CSV
with open(CSV_FILENAME, "w", newline="", encoding="utf-8-sig") as file:
    writer = csv.writer(file)
    writer.writerow(["Дата", "Заголовок", "Ссылка"])  # Заголовки столбцов
    writer.writerows(news_data)

print(f"\nВсего собрано новостей: {len(news_data)}. Данные сохранены в '{CSV_FILENAME}'.")

# 4. Обработка данных и построение графика
if news_data:
    df = pd.read_csv(CSV_FILENAME)

    # Словарь сокращённых (и полных) названий месяцев
    months_map = {
        'янв': '01', 'фев': '02', 'мар': '03', 'апр': '04',
        'май': '05', 'мая': '05', 'июн': '06', 'июл': '07',
        'авг': '08', 'сен': '09', 'окт': '10', 'ноя': '11', 'дек': '12'
    }

    current_year = pd.Timestamp.now().year

    def parse_short_date(date_str):
        if not isinstance(date_str, str):
            return pd.NaT
        
        # Приводим к нижнему регистру и убираем лишнее (например, точки после сокращений)
        date_str = date_str.strip().lower().replace(".", "")
        parts = date_str.split()

        if len(parts) < 2:
            return pd.NaT

        day = parts[0]
        month_str = parts[1]
        
        # Если год указан (например, "15 сен 2024"), берем его, иначе берем текущий
        year = parts[2] if len(parts) >= 3 and parts[2].isdigit() else str(current_year)

        # Подставляем номер месяца
        month = months_map.get(month_str[:3])
        if not month:
            return pd.NaT

        try:
            return pd.to_datetime(f"{day}.{month}.{year}", format="%d.%m.%Y")
        except Exception:
            return pd.NaT

    # Применяем функцию парсинга
    df["Дата"] = df["Дата"].apply(parse_short_date)
    
    # Удаляем нераспознанные даты
    df = df.dropna(subset=["Дата"])

    if df.empty:
        print("Ошибка: Не удалось распарсить даты. Проверьте CSV-файл.")
    else:
        # Группируем по месяцам и сортируем по хронологии
        df["Год-Месяц"] = df["Дата"].dt.to_period("M")
        news_by_month = df.groupby("Год-Месяц").size().sort_index()

        # Построение графика
        plt.figure(figsize=(12, 6))
        
        x_labels = news_by_month.index.astype(str)
        plt.bar(x_labels, news_by_month.values, color="skyblue", edgecolor="black")
        
        plt.title("Распределение количества новостей категории 'Наука' по месяцам (МАИ)")
        plt.xlabel("Период (Год-Месяц)")
        plt.ylabel("Количество новостей")
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        
        plt.tight_layout()
        plt.savefig("news_distribution.png")
        print("График успешно сохранен в 'news_distribution.png'")
        plt.show()