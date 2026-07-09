
import asyncpg
from config import DATABASE_URL

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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL)
    return _pool

async def init_db():
    pool = await get_pool()
    async with pool.acquire() as db:
        await db.execute(CREATE_TABLE_SQL)

async def upsert_trader_field(uid: str, **fields):
    if not fields:
        return
    pool = await get_pool()
    async with pool.acquire() as db:
        exists = await db.fetchval("SELECT uid FROM traders WHERE uid=$1", uid)
        if exists:
            sets = ", ".join([f"{k}=${i+1}" for i,k in enumerate(fields.keys())])
            values=list(fields.values())+[uid]
            await db.execute(
                f"UPDATE traders SET {sets}, updated_at=CURRENT_TIMESTAMP WHERE uid=${len(values)}",
                *values
            )
        else:
            cols=["uid"]+list(fields.keys())
            vals=[uid]+list(fields.values())
            placeholders=", ".join([f"${i+1}" for i in range(len(vals))])
            await db.execute(
                f"INSERT INTO traders ({', '.join(cols)}) VALUES ({placeholders})",
                *vals
            )

async def get_trader(uid: str):
    pool=await get_pool()
    async with pool.acquire() as db:
        row=await db.fetchrow("SELECT * FROM traders WHERE uid=$1", uid)
        return dict(row) if row else None

async def link_telegram_chat(uid, chat_id):
    await upsert_trader_field(uid, telegram_chat_id=str(chat_id))

async def get_all_chat_ids():
    pool=await get_pool()
    async with pool.acquire() as db:
        rows=await db.fetch("SELECT DISTINCT telegram_chat_id FROM traders WHERE telegram_chat_id IS NOT NULL")
        return [r["telegram_chat_id"] for r in rows]

async def get_stats():
    pool=await get_pool()
    async with pool.acquire() as db:
        total=await db.fetchval("SELECT COUNT(*) FROM traders")
        with_chats=await db.fetchval("SELECT COUNT(*) FROM traders WHERE telegram_chat_id IS NOT NULL")
        with_deposit=await db.fetchval(
            """
            SELECT COUNT(*) FROM traders
            WHERE
                CASE
                    WHEN COALESCE(NULLIF(balance, ''), NULLIF(ftd_amount, ''), NULLIF(sum_of_deposits, ''), NULLIF(count_of_deposits, ''), '0') ~ '^[0-9]+(\\.[0-9]+)?$'
                    THEN COALESCE(NULLIF(balance, ''), NULLIF(ftd_amount, ''), NULLIF(sum_of_deposits, ''), NULLIF(count_of_deposits, ''), '0')::numeric
                    ELSE 0
                END > 0
            """
        )
        return {
            "total": total,
            "with_chats": with_chats,
            "with_deposit": with_deposit,
        }

async def get_inactive_traders(days:int):
    pool=await get_pool()
    async with pool.acquire() as db:
        rows=await db.fetch(
            "SELECT * FROM traders WHERE telegram_chat_id IS NOT NULL AND updated_at <= NOW() - ($1 || ' days')::interval",
            str(days)
        )
        return [dict(r) for r in rows]
