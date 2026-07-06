import os

# --- Обязательные переменные окружения ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "max_supportTraide")

# Ссылки на регистрацию (по ГЕО)
REG_LINK_RU = os.getenv(
    "REG_LINK_RU",
    "https://po-ru4.click/register?utm_campaign=820172&utm_source=affiliate&utm_medium=sr&a=SLjZBE1edTSNUa&ac=telega",
)
REG_LINK_OTHER = os.getenv(
    "REG_LINK_OTHER",
    "https://u3.shortink.io/register?utm_campaign=820172&utm_source=affiliate&utm_medium=sr&a=SLjZBE1edTSNUa&ac=telega",
)

# Путь к базе данных (файл SQLite, лежит рядом с кодом)
DB_PATH = os.getenv("DB_PATH", "traders.db")

# Порт для приёма постбеков (Railway сам подставит переменную PORT)
POSTBACK_PORT = int(os.getenv("PORT", "8080"))

# Секретный токен постбека (опционально, но рекомендуется).
# Если задан — постбек должен содержать ?secret=ЗНАЧЕНИЕ, иначе будет отклонён.
# Это защищает эндпоинт от посторонних запросов.
POSTBACK_SECRET = os.getenv("POSTBACK_SECRET", "")

# --- Опционально: интеграция ИИ для классификации вопросов (FAQ) ---
# Оставлено пустым по умолчанию — бот работает по чёткому скрипту и без ИИ.
# Если захотите подключить (Claude/OpenAI/DeepSeek — любой), впишите ключ и
# провайдера, и допишите функцию classify_intent() в ai_helper.py
AI_PROVIDER = os.getenv("AI_PROVIDER", "")  # например: "anthropic", "openai", "deepseek"
AI_API_KEY = os.getenv("AI_API_KEY", "")
