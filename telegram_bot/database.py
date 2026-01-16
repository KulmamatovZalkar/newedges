"""
Database connection and operations for the bot.
Uses PostgreSQL with asyncpg/psycopg2.
"""
import os
import logging
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# Database connection pool
_connection_params: Dict[str, Any] = {}


def parse_database_url(url: str) -> Dict[str, Any]:
    """Parse DATABASE_URL into connection parameters."""
    # Format: postgres://user:password@host:port/database
    url = url.replace('postgres://', '').replace('postgresql://', '')
    
    # Split user:password@host:port/database
    auth_host, database = url.rsplit('/', 1)
    auth, host_port = auth_host.rsplit('@', 1)
    user, password = auth.split(':')
    
    if ':' in host_port:
        host, port = host_port.split(':')
    else:
        host = host_port
        port = '5432'
    
    return {
        'host': host,
        'port': int(port),
        'database': database,
        'user': user,
        'password': password
    }


async def init_db():
    """Initialize database connection parameters."""
    global _connection_params
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable is not set!")
        raise ValueError("DATABASE_URL is required")
    
    _connection_params = parse_database_url(database_url)
    logger.info(f"Database connection initialized: {_connection_params['host']}:{_connection_params['port']}")


def get_connection():
    """Get a database connection."""
    return psycopg2.connect(**_connection_params, cursor_factory=RealDictCursor)


def get_bot_token_from_db() -> Optional[str]:
    """Get bot token from database settings."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT bot_token FROM bot_admin_botsettings WHERE id = 1 AND bot_token IS NOT NULL AND bot_token != ''"
                )
                result = cur.fetchone()
                if result:
                    return result['bot_token']
    except Exception:
        pass
    return None


# User operations
def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None, last_name: str = None) -> Dict:
    """Get or create a user profile."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Try to get existing user
            cur.execute(
                "SELECT * FROM bot_admin_userprofile WHERE telegram_id = %s",
                (telegram_id,)
            )
            user = cur.fetchone()
            
            if user:
                return dict(user)
            
            # Create new user
            cur.execute(
                """
                INSERT INTO bot_admin_userprofile 
                (telegram_id, username, first_name, last_name, is_team_member, is_registration_complete, created_at, updated_at)
                VALUES (%s, %s, %s, %s, FALSE, FALSE, NOW(), NOW())
                RETURNING *
                """,
                (telegram_id, username, first_name, last_name)
            )
            conn.commit()
            return dict(cur.fetchone())


def update_user(telegram_id: int, **kwargs) -> Dict:
    """Update user profile fields."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            set_clause = ", ".join([f"{k} = %s" for k in kwargs.keys()])
            set_clause += ", updated_at = NOW()"
            values = list(kwargs.values()) + [telegram_id]
            
            cur.execute(
                f"UPDATE bot_admin_userprofile SET {set_clause} WHERE telegram_id = %s RETURNING *",
                values
            )
            conn.commit()
            return dict(cur.fetchone())


def set_current_question(telegram_id: int, question_id: Optional[int]):
    """Set current question for user."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE bot_admin_userprofile SET current_question_id = %s, updated_at = NOW() WHERE telegram_id = %s",
                (question_id, telegram_id)
            )
            conn.commit()


def get_user(telegram_id: int) -> Optional[Dict]:
    """Get user by telegram_id."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM bot_admin_userprofile WHERE telegram_id = %s",
                (telegram_id,)
            )
            result = cur.fetchone()
            return dict(result) if result else None


# Question operations
def get_questions() -> List[Dict]:
    """Get all active questions ordered by order."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM bot_admin_question WHERE is_active = TRUE ORDER BY \"order\""
            )
            return [dict(row) for row in cur.fetchall()]


def get_question_by_id(question_id: int) -> Optional[Dict]:
    """Get question by ID."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM bot_admin_question WHERE id = %s",
                (question_id,)
            )
            result = cur.fetchone()
            return dict(result) if result else None


def get_next_question(current_order: int) -> Optional[Dict]:
    """Get next question after current order."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM bot_admin_question 
                WHERE is_active = TRUE AND \"order\" > %s 
                ORDER BY \"order\" 
                LIMIT 1
                """,
                (current_order,)
            )
            result = cur.fetchone()
            return dict(result) if result else None


def get_first_question() -> Optional[Dict]:
    """Get first active question."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM bot_admin_question WHERE is_active = TRUE ORDER BY \"order\" LIMIT 1"
            )
            result = cur.fetchone()
            return dict(result) if result else None


# Response operations
def save_response(user_id: int, question_id: int, text_answer: str = None, photo_path: str = None):
    """Save or update user response."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Check if response exists
            cur.execute(
                """
                SELECT id FROM bot_admin_userresponse 
                WHERE user_id = %s AND question_id = %s
                """,
                (user_id, question_id)
            )
            existing = cur.fetchone()
            
            if existing:
                # Update existing
                cur.execute(
                    """
                    UPDATE bot_admin_userresponse 
                    SET text_answer = %s, photo = %s, updated_at = NOW()
                    WHERE user_id = %s AND question_id = %s
                    """,
                    (text_answer, photo_path, user_id, question_id)
                )
            else:
                # Create new
                cur.execute(
                    """
                    INSERT INTO bot_admin_userresponse 
                    (user_id, question_id, text_answer, photo, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                    """,
                    (user_id, question_id, text_answer, photo_path)
                )
            conn.commit()


def get_user_responses(telegram_id: int) -> List[Dict]:
    """Get all responses for a user."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.*, q.text as question_text, q.field_name
                FROM bot_admin_userresponse r
                JOIN bot_admin_userprofile u ON r.user_id = u.id
                JOIN bot_admin_question q ON r.question_id = q.id
                WHERE u.telegram_id = %s
                ORDER BY q."order"
                """,
                (telegram_id,)
            )
            return [dict(row) for row in cur.fetchall()]


# StaffApplication operations
def get_or_create_application(user_id: int) -> Dict:
    """Get or create a staff application for user."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Try to get existing application
            cur.execute(
                "SELECT * FROM bot_admin_staffapplication WHERE user_id = %s",
                (user_id,)
            )
            app = cur.fetchone()
            
            if app:
                return dict(app)
            
            # Create new application
            cur.execute(
                """
                INSERT INTO bot_admin_staffapplication 
                (user_id, status, created_at, updated_at)
                VALUES (%s, 'in_progress', NOW(), NOW())
                RETURNING *
                """,
                (user_id,)
            )
            conn.commit()
            return dict(cur.fetchone())


def update_application(user_id: int, **kwargs) -> Dict:
    """Update application fields by user_id."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            set_parts = []
            values = []
            
            for key, value in kwargs.items():
                set_parts.append(f"{key} = %s")
                values.append(value)
            
            set_parts.append("updated_at = NOW()")
            values.append(user_id)
            
            set_clause = ", ".join(set_parts)
            
            cur.execute(
                f"UPDATE bot_admin_staffapplication SET {set_clause} WHERE user_id = %s RETURNING *",
                values
            )
            conn.commit()
            result = cur.fetchone()
            return dict(result) if result else None


def complete_application(user_id: int) -> Dict:
    """Mark application as completed."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE bot_admin_staffapplication 
                SET status = 'completed', completed_at = NOW(), updated_at = NOW()
                WHERE user_id = %s
                RETURNING *
                """,
                (user_id,)
            )
            conn.commit()
            result = cur.fetchone()
            return dict(result) if result else None


def get_application_by_telegram_id(telegram_id: int) -> Optional[Dict]:
    """Get application by telegram_id."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.* FROM bot_admin_staffapplication a
                JOIN bot_admin_userprofile u ON a.user_id = u.id
                WHERE u.telegram_id = %s
                """,
                (telegram_id,)
            )
            result = cur.fetchone()
            return dict(result) if result else None

