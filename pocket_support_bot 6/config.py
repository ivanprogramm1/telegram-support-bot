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

# Асеты (картинки, голосовые)
VERIFICATION_IMAGES = [
    "assets/verification_1.jpg",
    "assets/verification_2.jpg",
    "assets/verification_3.jpg",
]

WORKFLOW_IMAGES = [
    "assets/workflow_1.jpg",
    "assets/workflow_2.jpg",
    "assets/workflow_3.jpg",
    "assets/workflow_4.jpg",
]

VOICE_WARNINGS = [
    "assets/voice_risks.ogg",
    "assets/voice_rules.ogg",
]

# Порт для приёма постбеков (Railway сам подставит переменную PORT)
POSTBACK_PORT = int(os.getenv("PORT", "8080"))

# Секретный токен постбека (опционально, но рекомендуется).
# Если задан — постбек должен содержать ?secret=ЗНАЧЕНИЕ, иначе будет отклонён.
# Это защищает эндпоинт от посторонних запросов.
POSTBACK_SECRET = os.getenv("POSTBACK_SECRET", "")

# Ваш личный Telegram ID (не username, а числовой ID) — нужен, чтобы только
# вы могли подтверждать верификацию командой /verify. Узнать свой ID можно,
# написав боту @userinfobot в Telegram.
OWNER_TELEGRAM_ID = os.getenv("OWNER_TELEGRAM_ID", "")

# Через запятую: ID каналов/групп, откуда бот будет убирать неактивных
# участников. Бот должен быть администратором в каждом из них.
# Пример: CHANNEL_IDS=-1001234567890,-1009876543210
CHANNEL_IDS = [
    c.strip() for c in os.getenv("CHANNEL_IDS", "").split(",") if c.strip()
]

# Через сколько дней без единого postback-события (депозит/вывод/комиссия
# и т.п.) считать пользователя неактивным
INACTIVITY_DAYS = int(os.getenv("INACTIVITY_DAYS", "30"))

# --- Опционально: интеграция ИИ для классификации вопросов (FAQ) ---
# Оставлено пустым по умолчанию — бот работает по чёткому скрипту и без ИИ.
# Если захотите подключить (Claude/OpenAI/DeepSeek — любой), впишите ключ и
# провайдера, и допишите функцию classify_intent() в ai_helper.py
AI_PROVIDER = os.getenv("AI_PROVIDER", "")  # например: "anthropic", "openai", "deepseek"
AI_API_KEY = os.getenv("AI_API_KEY", "")
