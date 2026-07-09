import aiosqlite
from config import DB_PATH

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS traders (
    uid TEXT PRIMARY KEY,
    reg_date TEXT,
    activity_date TEXT,
    country TEXT,
    verified TEXT,
    balance TEXT,
    ftd_amount TEXT,
    ftd_date TEXT,
    count_of_deposits TEXT,
    sum_of_deposits TEXT,
    sum_of_bonuses TEXT,
    count_of_bonuses TEXT,
    self_excluded TEXT,
    commission TEXT,
    link_type TEXT,
    link TEXT,
    telegram_chat_id TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_TABLE_SQL)
        await db.commit()


async def upsert_trader_field(uid: str, **fields):
    """
    Обновляет (или создаёт) запись трейдера. Принимает только те поля,
    которые реально пришли в постбеке — остальные не трогает.
    Пример вызова: upsert_trader_field("136296754", reg_date="2026-07-05", country="Russia")
    """
    if not fields:
        return

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT uid FROM traders WHERE uid = ?", (uid,))
        row = await cursor.fetchone()

        if row is None:
            columns = ["uid"] + list(fields.keys())
            placeholders = ", ".join(["?"] * len(columns))
            values = [uid] + list(fields.values())
            await db.execute(
                f"INSERT INTO traders ({', '.join(columns)}) VALUES ({placeholders})",
                values,
            )
        else:
            set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
            values = list(fields.values()) + [uid]
            await db.execute(
                f"UPDATE traders SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE uid = ?",
                values,
            )
        await db.commit()


async def get_trader(uid: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM traders WHERE uid = ?", (uid,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def link_telegram_chat(uid: str, chat_id: str):
    """Привязывает Telegram chat_id пользователя к его UID (чтобы бот знал, кому писать)."""
    await upsert_trader_field(uid, telegram_chat_id=str(chat_id))


async def get_all_chat_ids():
    """Все telegram_chat_id пользователей, которые хоть раз писали боту (для рассылки)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT DISTINCT telegram_chat_id FROM traders WHERE telegram_chat_id IS NOT NULL"
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def get_inactive_traders(days: int):
    """
    Трейдеры, у которых telegram_chat_id известен, но уже давно (>= days)
    не приходило ни одного postback-события (updated_at не менялся).
    Это приближённая метрика активности — не то же самое, что "баланс не
    меняется", но ближайшее, что можно отследить доступными данными.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM traders
            WHERE telegram_chat_id IS NOT NULL
            AND updated_at <= datetime('now', ? || ' days')
            """,
            (f"-{days}",),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
