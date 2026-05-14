import json
import aiosqlite
import logging
from datetime import datetime

DB_PATH = "users.db"
logger = logging.getLogger(__name__)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                phone TEXT,
                language TEXT DEFAULT 'ru',
                is_subscribed INTEGER DEFAULT 0,
                video_watched INTEGER DEFAULT 0,
                video_sent_at TIMESTAMP,
                product_chosen TEXT,
                paid INTEGER DEFAULT 0,
                warmup_sent INTEGER DEFAULT 0,
                warmup_answer_1 TEXT,
                warmup_answer_2 TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_key TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                warned INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_key TEXT NOT NULL,
                photo_file_id TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                processed_by INTEGER,
                decline_reason TEXT,
                admin_messages TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


# ─── Users ───────────────────────────────────────────────────────────────────

async def get_user(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_or_update_user(user_id: int, username: str, first_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
            """,
            (user_id, username, first_name),
        )
        await db.commit()


async def update_user(user_id: int, **kwargs):
    if not kwargs:
        return
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {fields} WHERE user_id = ?", values)
        await db.commit()


async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]


# ─── Payments ────────────────────────────────────────────────────────────────

async def create_pending_payment(user_id: int, product_key: str, photo_file_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO pending_payments (user_id, product_key, photo_file_id) VALUES (?, ?, ?)",
            (user_id, product_key, photo_file_id),
        )
        await db.commit()
        return cursor.lastrowid


async def get_pending_payment(payment_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM pending_payments WHERE id = ?", (payment_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_payment(payment_id: int, **kwargs):
    if not kwargs:
        return
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [payment_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE pending_payments SET {fields} WHERE id = ?", values)
        await db.commit()


async def save_admin_message(payment_id: int, admin_id: int, message_id: int):
    """Store {admin_id: message_id} mapping so we can edit all admin messages later."""
    payment = await get_pending_payment(payment_id)
    if not payment:
        return
    messages = json.loads(payment.get("admin_messages") or "{}")
    messages[str(admin_id)] = message_id
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE pending_payments SET admin_messages = ? WHERE id = ?",
            (json.dumps(messages), payment_id),
        )
        await db.commit()


async def get_admin_messages(payment_id: int) -> dict[str, int]:
    payment = await get_pending_payment(payment_id)
    if not payment:
        return {}
    return json.loads(payment.get("admin_messages") or "{}")


# ─── Subscriptions ───────────────────────────────────────────────────────────

async def create_subscription(user_id: int, product_key: str, channel_id: str, expires_at: datetime):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO subscriptions (user_id, product_key, channel_id, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, product_key, channel_id, expires_at.isoformat()),
        )
        await db.commit()


async def get_expiring_soon(hours_ahead: int = 24) -> list[dict]:
    """Subscriptions expiring within `hours_ahead` hours that haven't been warned yet."""
    from datetime import timedelta
    now = datetime.now()
    deadline = now + timedelta(hours=hours_ahead)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM subscriptions
            WHERE expires_at <= ? AND expires_at > ? AND warned = 0
            """,
            (deadline.isoformat(), now.isoformat()),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_expired() -> list[dict]:
    now = datetime.now()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM subscriptions WHERE expires_at <= ? AND warned = 1",
            (now.isoformat(),),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def mark_warned(sub_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE subscriptions SET warned = 1 WHERE id = ?", (sub_id,))
        await db.commit()


async def delete_subscription(sub_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM subscriptions WHERE id = ?", (sub_id,))
        await db.commit()
