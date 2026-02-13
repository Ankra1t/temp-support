import sqlite3
from typing import Optional, Dict, Any
from datetime import datetime
from settings import DATABASE_PATH


class Database:
    """Класс для работы с SQLite базой данных пользователей бота."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DATABASE_PATH
        self.init_db()

    def get_connection(self):
        """Создаёт и возвращает новое соединение с БД."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Создаёт таблицу bot_users если не существует."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL UNIQUE,
                topic_id INTEGER,
                platform VARCHAR(50) DEFAULT 'telegram',
                is_banned BOOLEAN DEFAULT 0,
                banned_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_bot_users_chat_id
            ON bot_users(chat_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_bot_users_topic_id
            ON bot_users(topic_id)
        ''')

        conn.commit()
        conn.close()

    def get_user_by_chat_id(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Получает пользователя по chat_id."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM bot_users WHERE chat_id = ?',
            (chat_id,)
        )

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def get_user_by_topic_id(self, topic_id: int) -> Optional[Dict[str, Any]]:
        """Получает пользователя по topic_id."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM bot_users WHERE topic_id = ?',
            (topic_id,)
        )

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def create_user(self, chat_id: int, platform: str = 'telegram') -> Dict[str, Any]:
        """Создаёт нового пользователя."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            '''INSERT INTO bot_users (chat_id, platform)
               VALUES (?, ?)''',
            (chat_id, platform)
        )

        conn.commit()

        cursor.execute(
            'SELECT * FROM bot_users WHERE id = ?',
            (cursor.lastrowid,)
        )

        row = cursor.fetchone()
        conn.close()

        return dict(row)

    def update_user_topic(self, chat_id: int, topic_id: int) -> bool:
        """Обновляет topic_id пользователя."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            '''UPDATE bot_users
               SET topic_id = ?, updated_at = ?
               WHERE chat_id = ?''',
            (topic_id, datetime.now(), chat_id)
        )

        conn.commit()
        result = cursor.rowcount > 0
        conn.close()

        return result

    def ban_user(self, chat_id: int) -> bool:
        """Банит пользователя."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            '''UPDATE bot_users
               SET is_banned = 1, banned_at = ?
               WHERE chat_id = ?''',
            (datetime.now(), chat_id)
        )

        conn.commit()
        result = cursor.rowcount > 0
        conn.close()

        return result

    def unban_user(self, chat_id: int) -> bool:
        """Разбанивает пользователя."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            '''UPDATE bot_users
               SET is_banned = 0, banned_at = NULL
               WHERE chat_id = ?''',
            (chat_id,)
        )

        conn.commit()
        result = cursor.rowcount > 0
        conn.close()

        return result


# Глобальный экземпляр базы данных
db = Database()


# Функции-обёртки для удобного использования
def get_user_by_chat_id(chat_id: int) -> Optional[Dict[str, Any]]:
    """Получает пользователя по chat_id."""
    return db.get_user_by_chat_id(chat_id)


def get_user_by_topic_id(topic_id: int) -> Optional[Dict[str, Any]]:
    """Получает пользователя по topic_id."""
    return db.get_user_by_topic_id(topic_id)


def create_user(chat_id: int, platform: str = 'telegram') -> Dict[str, Any]:
    """Создаёт нового пользователя."""
    return db.create_user(chat_id, platform)


def update_user_topic(chat_id: int, topic_id: int) -> bool:
    """Обновляет topic_id пользователя."""
    return db.update_user_topic(chat_id, topic_id)


def ban_user(chat_id: int) -> bool:
    """Банит пользователя."""
    return db.ban_user(chat_id)


def unban_user(chat_id: int) -> bool:
    """Разбанивает пользователя."""
    return db.unban_user(chat_id)
