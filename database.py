import aiosqlite
from pathlib import Path

DB_PATH = Path("database/guard.db")


class Database:

    def __init__(self):
        self.db = DB_PATH

    async def connect(self):
        return await aiosqlite.connect(self.db)

    async def setup(self):
        async with aiosqlite.connect(self.db) as db:

            # إعدادات السيرفرات
            await db.execute("""
            CREATE TABLE IF NOT EXISTS guilds(
                guild_id INTEGER PRIMARY KEY,
                owner_id INTEGER DEFAULT NULL,
                language TEXT DEFAULT 'ar',
                antinuke INTEGER DEFAULT 1,
                punishment TEXT DEFAULT 'jail',
                logs_channel INTEGER DEFAULT NULL,
                welcome_channel INTEGER DEFAULT NULL,
                jail_role INTEGER DEFAULT NULL,
                jail_channel INTEGER DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # ملاك السيرفر
            await db.execute("""
            CREATE TABLE IF NOT EXISTS owners(
                guild_id INTEGER,
                user_id INTEGER,
                added_by INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # الأشخاص المحميون
            await db.execute("""
            CREATE TABLE IF NOT EXISTS protected_users(
                guild_id INTEGER,
                user_id INTEGER
            )
            """)

            # الرتب المحمية
            await db.execute("""
            CREATE TABLE IF NOT EXISTS protected_roles(
                guild_id INTEGER,
                role_id INTEGER
            )
            """)

            # التوقيف
            await db.execute("""
            CREATE TABLE IF NOT EXISTS jailed(
                guild_id INTEGER,
                user_id INTEGER,
                roles TEXT,
                reason TEXT,
                until_time INTEGER,
                jailed_by INTEGER
            )
            """)

            # التحذيرات
            await db.execute("""
            CREATE TABLE IF NOT EXISTS warns(
                guild_id INTEGER,
                user_id INTEGER,
                moderator INTEGER,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            await db.commit()


database = Database()