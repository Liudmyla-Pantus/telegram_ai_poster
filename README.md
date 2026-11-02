# M4 — AI-генератор постів для Telegram

Навчальний backend-сервіс на FastAPI, який збирає новини із сайтів і публічних
Telegram-каналів, видаляє дублікати, фільтрує матеріали, створює дописи через
OpenAI та після явного підтвердження публікує їх у Telegram.

За замовчуванням увімкнений безпечний `TEST_MODE=true`: AI-відповідь генерується
локально, а надсилання в Telegram заблоковане. Тому проєкт можна перевіряти без
ключів і без ризику випадкової публікації.

## Можливості

- універсальний HTML-парсер на `requests` + `BeautifulSoup`;
- читання публічних каналів через `Telethon`;
- SQLite та SQLAlchemy 2;
- захист від дублів за URL, нормалізованим заголовком і hash контенту;
- ключові слова, мова та прив'язка до джерела;
- OpenAI Responses API та обробка rate limit/мережевих помилок;
- Celery pipeline і Celery Beat раз на 30 хвилин;
- історія постів, статуси та журнал помилок;
- Swagger, pytest і ручні API-операції.

## Структура

```text
telegram_ai_poster/
├── aibot/
│   ├── app/
│   │   ├── api/              # endpoints та Pydantic-схеми
│   │   ├── ai/               # prompt та OpenAI client
│   │   ├── news_parser/      # парсери сайтів і Telegram
│   │   ├── telegram/         # Telethon publisher
│   │   ├── config.py         # налаштування з .env
│   │   ├── database.py       # engine та сесії SQLAlchemy
│   │   ├── models.py         # таблиці БД
│   │   ├── services.py       # збереження й дедуплікація
│   │   ├── tasks.py          # Celery tasks і Beat
│   │   └── main.py           # FastAPI
│   └── celery_worker.py
├── tests/
├── .env.example
├── requirements.txt
└── CHECKLIST.md
```

## 1. Відкриття в PyCharm на macOS

1. Відкрийте PyCharm → **Open**.
2. Виберіть папку `telegram_ai_poster` (не лише папку `aibot`).
3. Натисніть **Trust Project**, якщо PyCharm запитає.
4. Відкрийте вбудований Terminal внизу вікна.

## 2. Віртуальне середовище

У Terminal із кореня проєкту:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
```

Потрібен Python 3.11 або новіший. У PyCharm інтерпретатор можна перевірити через
**Settings → Project → Python Interpreter** і вибрати `.venv/bin/python`.

## 3. Встановлення бібліотек

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Файл `.env` не потрапляє в Git. Не записуйте секрети у Python-файли.

## 4. Запуск FastAPI

```bash
uvicorn aibot.app.main:app --reload
```

Перевірка: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health).
Зупинка сервера: `Control+C`.

## 5. Swagger

Після запуску відкрийте [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
Кнопка **Try it out** дозволяє виконувати запити без Postman.

Основні маршрути:

| Метод | URL | Призначення |
|---|---|---|
| GET/POST | `/api/sources/` | список і створення джерел |
| GET/PATCH/DELETE | `/api/sources/{id}` | робота з одним джерелом |
| GET/POST | `/api/keywords/` | ключові слова |
| PATCH/DELETE | `/api/keywords/{id}` | зміна або видалення слова |
| GET/POST | `/api/news/` | новини та ручне додавання |
| GET/DELETE | `/api/news/{id}` | перегляд або видалення новини |
| POST | `/api/collect/` | поставити збір у Celery |
| POST | `/api/generate/` | тестова/ручна генерація |
| GET | `/api/posts/` | історія постів |
| GET | `/api/posts/{id}` | один згенерований пост |
| POST | `/api/posts/{id}/publish` | публікація з підтвердженням |
| GET | `/api/errors/` | останні помилки інтеграцій |

Приклад джерела-сайту:

```json
{
  "type": "site",
  "name": "Example News",
  "url": "https://example.com/news",
  "enabled": true,
  "language": "uk"
}
```

Telegram-джерело має `"type": "tg"`, а `url` містить `@channel_username`.

## 6. Redis, Celery Worker і Beat

Найпростіше встановити Redis через Homebrew:

```bash
brew install redis
brew services start redis
redis-cli ping
```

Очікувана відповідь — `PONG`. Далі відкрийте два окремі термінали (в обох
активуйте `.venv`). У першому запустіть worker:

```bash
celery -A aibot.app.tasks:celery_app worker --loglevel=info
```

У другому — планувальник:

```bash
celery -A aibot.app.tasks:celery_app beat --loglevel=info
```

Beat ставить `collect_all` у чергу кожні 1800 секунд. Worker збирає ввімкнені
джерела, зберігає нові записи, фільтрує їх та генерує пости для релевантних новин.
Повний автоматичний крок публікації виконується лише при `AUTO_PUBLISH=true` та
`TEST_MODE=false`; типове значення навмисно безпечне — `AUTO_PUBLISH=false`.
Для ручного збору Redis і worker також повинні працювати.

## 7. OpenAI API

1. Створіть API key у своєму OpenAI-акаунті.
2. У `.env` заповніть `OPENAI_API_KEY` та за потреби змініть `OPENAI_MODEL`.
3. Лише коли готові до реальних API-викликів, встановіть `TEST_MODE=false`.
4. Перезапустіть FastAPI і Celery worker після зміни `.env`.

API OpenAI є зовнішнім платним сервісом; потрібні активний ключ, доступ до моделі
та інтернет. У `TEST_MODE=true` ключ не потрібен.

## 8. Telegram і Telethon

1. На [my.telegram.org/apps](https://my.telegram.org/apps) створіть застосунок.
2. Запишіть `api_id` та `api_hash` у відповідні змінні `.env`.
3. Вкажіть `TELEGRAM_TARGET_CHANNEL=@назва_каналу`.
4. Обліковий запис має бути адміністратором цільового каналу.
5. Перший запуск Telethon може попросити телефон, код входу та пароль 2FA у
   терміналі; файл сесії зберігається локально та ігнорується Git.

Навіть з `confirm=true` публікація заблокована, поки `TEST_MODE=true`. Для реальної
публікації треба свідомо виконати обидві дії: встановити `TEST_MODE=false` і
надіслати `POST /api/posts/{id}/publish` з тілом `{"confirm": true}`.

## 9. Тестування

```bash
pytest
```

Тести використовують окрему SQLite БД у пам'яті, не викликають OpenAI та нічого
не надсилають у Telegram. Вони перевіряють запуск FastAPI/Swagger, CRUD API,
збереження, фільтрацію, дублікати, тестову генерацію та Celery tasks.

Ручна коротка перевірка:

1. Запустіть FastAPI, Redis, worker і Beat.
2. У Swagger створіть ключове слово та джерело.
3. Запустіть `/api/collect/`.
4. Перегляньте `/api/news/`, `/api/posts/` і `/api/errors/`.
5. Перевірте `/api/generate/` із власним текстом.

Універсальний HTML-парсер розрахований на семантичні `article`, заголовки та
посилання. Якщо конкретний сайт має нестандартну розмітку або забороняє scraping,
для нього слід створити окремий parser у `news_parser/`, як вимагає ТЗ.

## 10. Підготовка до здачі

1. Залиште `TEST_MODE=true` і переконайтеся, що `.env` не відстежується Git.
2. Запустіть `pytest` і збережіть успішний результат або скриншот.
3. Перевірте [CHECKLIST.md](CHECKLIST.md).
4. Перегляньте `git status`, створіть commit і завантажте репозиторій на GitHub.
5. За бажанням додайте скриншоти Swagger та короткий скринкаст.
6. Надішліть викладачеві посилання, ПІБ і номер групи.

Не додавайте в репозиторій `.env`, `*.session`, базу SQLite або реальні ключі.

## Важливі навчальні пояснення

- FastAPI обробляє HTTP-запити, але важкий збір виконує Celery worker.
- Redis є брокером: зберігає чергу завдань між API/Beat і worker.
- SQLAlchemy перетворює Python-моделі на таблиці SQLite.
- Pydantic перевіряє вхідні JSON-дані до виконання бізнес-логіки.
- Fingerprint — SHA-256 від нормалізованих title, URL і контенту.
- `Post.status` показує етап: `new`, `generated`, `published` або `failed`.
