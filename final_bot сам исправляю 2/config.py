# config.py

import os


# ==========================
# BOT
# ==========================

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

SUPPORT_USERNAME = os.getenv(
    "SUPPORT_USERNAME",
    "max_supportTraide"
)


# ==========================
# DATABASE
# ==========================

DB_PATH = os.getenv(
    "DB_PATH",
    "traders.db"
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost/traders"
)


# ==========================
# POSTBACK
# ==========================

POSTBACK_PORT = int(
    os.getenv("PORT", "8080")
)

POSTBACK_SECRET = os.getenv(
    "POSTBACK_SECRET",
    ""
)


# ==========================
# ADMINS
# ==========================

OWNER_TELEGRAM_IDS = [
    x.strip()
    for x in os.getenv(
        "OWNER_TELEGRAM_IDS",
        "620965365,1232402162,8105867317"
    ).split(",")
    if x.strip()
]


OWNER_TELEGRAM_ID = (
    OWNER_TELEGRAM_IDS[0]
    if OWNER_TELEGRAM_IDS
    else ""
)


INACTIVITY_CHECK_INTERVAL_DAYS = int(
    os.getenv(
        "INACTIVITY_CHECK_INTERVAL_DAYS",
        "21"
    )
)



# ==========================
# CHANNELS
# ==========================

CHANNEL_IDS = [
    x.strip()
    for x in os.getenv(
        "CHANNEL_IDS",
        "2596783036,2512383728,3395872076"
    ).split(",")
    if x.strip()
]


INACTIVITY_DAYS = int(
    os.getenv(
        "INACTIVITY_DAYS",
        "21"
    )
)



# ==========================
# LINKS
# ==========================

SUPPORT_LINK = (
    f"https://t.me/{SUPPORT_USERNAME}"
)


CHANNEL_FAMILY_LINK = (
    "https://t.me/+pJOy7XUwq6FjMDky"
)


ROBOT_LINK = (
    "https://t.me/+5W19mCdyYl9hZmEy"
)


CHANNEL_OTC_LINK = (
    "https://t.me/+7AeJDGv4-DswYmZk"
)



# ==========================
# ASSETS
# ==========================


# Верификация

VERIFICATION_IMAGES = [
    "assets/verification_1.jpg",
    "assets/verification_2.jpg",
    "assets/verification_3.jpg",
]


# Скриншоты стратегии / работы

WORKFLOW_IMAGES = [
    "assets/workflow_1.jpg",
    "assets/workflow_2.jpg",
    "assets/workflow_3.jpg",
    "assets/workflow_4.jpg",
]



# Голосовые только после вступления в семью

FAMILY_VOICES = [
    "assets/family_voice_1.ogg",
    "assets/family_voice_2.ogg",
]



# ==========================
# AI
# ==========================

AI_PROVIDER = os.getenv(
    "AI_PROVIDER",
    ""
)


AI_API_KEY = os.getenv(
    "AI_API_KEY",
    ""
)
