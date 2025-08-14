import sqlite3
import logging
from typing import List, Dict, Optional

from utils.exceptions import (
    BotException,
    ParticipantNotFoundError,
    DuplicateParticipantError,
    ValidationError,
)

"""
===============================================================================
ПРАВИЛА ОБРАБОТКИ ИСКЛЮЧЕНИЙ В DATABASE LAYER
===============================================================================

🔍 ФУНКЦИИ ПОИСКА (get_*, find_*):
    - Возвращают None если запись не найдена
    - Бросают BotException только при реальных ошибках БД (connection, syntax, etc.)
    - НЕ бросают ParticipantNotFoundError

📝 ФУНКЦИИ ИЗМЕНЕНИЯ (add_*, update_*, delete_*):
    - Бросают ParticipantNotFoundError если запись не найдена для изменения
    - Бросают ValidationError при нарушении ограничений БД
    - Бросают BotException при ошибках БД

✅ ПРИМЕРЫ:
    get_participant_by_id(999) -> None (не найден)
    update_participant(999, data) -> ParticipantNotFoundError (не найден для изменения)
    add_participant(invalid_data) -> ValidationError (нарушены ограничения)

    # Правильное использование:
    participant = get_participant_by_id(123)
    if participant is None:
        print("Не найден")
    else:
        print(f"Найден: {participant['FullNameRU']}")
        
===============================================================================
"""

DB_PATH = "participants.db"
logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Context manager for SQLite connections with auto commit/rollback."""

    def __init__(self):
        self.conn: Optional[sqlite3.Connection] = None

    def __enter__(self) -> sqlite3.Connection:
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        sql_logger = logging.getLogger('sql')
        self.conn.set_trace_callback(sql_logger.info)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if not self.conn:
            return
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()


def _truncate_fields(data: Dict) -> Dict:
    """Truncate long text fields to fit DB limits."""
    result = data.copy()
    for field, limit in [('FullNameRU', 100), ('FullNameEN', 100), ('Church', 100)]:
        value = result.get(field)
        if value and len(value) > limit:
            logger.warning("%s truncated to %d chars", field, limit)
            result[field] = value[:limit]
    contact = result.get('ContactInformation')
    if contact and len(contact) > 200:
        logger.warning("ContactInformation truncated to 200 chars")
        result['ContactInformation'] = contact[:200]
    return result


def init_database():
    """Создание таблицы участников при первом запуске"""
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    FullNameRU TEXT NOT NULL,
                    Gender TEXT CHECK (Gender IN ('M', 'F')) DEFAULT 'F',
                    Size TEXT,
                    CountryAndCity TEXT,
                    Church TEXT,
                    Role TEXT CHECK (Role IN ('CANDIDATE', 'TEAM')) DEFAULT 'CANDIDATE',
                    Department TEXT,
                    FullNameEN TEXT,
                    SubmittedBy TEXT,
                    ContactInformation TEXT,
                    roomId INTEGER,
                    tableId INTEGER,
                    PaymentStatus TEXT DEFAULT 'Unpaid',
                    PaymentAmount INTEGER DEFAULT 0,
                    PaymentDate TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS Candidates_index_0
                ON participants (Size, Gender, FullNameRU, Department, Role)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS FullNameRU_index
                ON participants (FullNameRU)
                """
            )
            cursor.execute(
                """
                CREATE TRIGGER IF NOT EXISTS check_team_department
                BEFORE INSERT ON participants
                WHEN NEW.Role = 'TEAM' AND (NEW.Department IS NULL OR NEW.Department = '')
                BEGIN
                    SELECT RAISE(ABORT, 'Department is required for TEAM role');
                END;
                """
            )
            
            # Run migration to add payment fields to existing databases
            _migrate_payment_fields(cursor)
            
            print("✅ База данных инициализирована")
    except sqlite3.Error as e:
        logger.error("Error initializing database: %s", e)


def _migrate_payment_fields(cursor: sqlite3.Cursor) -> None:
    """Migration to add payment fields to existing databases."""
    try:
        # Check if payment fields already exist
        cursor.execute("PRAGMA table_info(participants)")
        columns = [column[1] for column in cursor.fetchall()]
        
        payment_fields_to_add = []
        if 'PaymentStatus' not in columns:
            payment_fields_to_add.append("PaymentStatus TEXT DEFAULT 'Unpaid'")
        if 'PaymentAmount' not in columns:
            payment_fields_to_add.append("PaymentAmount INTEGER DEFAULT 0")
        if 'PaymentDate' not in columns:
            payment_fields_to_add.append("PaymentDate TEXT DEFAULT ''")
        
        # Add missing payment fields
        for field_def in payment_fields_to_add:
            cursor.execute(f"ALTER TABLE participants ADD COLUMN {field_def}")
            logger.info(f"Added payment field: {field_def}")
        
        if payment_fields_to_add:
            print(f"✅ Миграция завершена: добавлено {len(payment_fields_to_add)} полей оплаты")
        
    except sqlite3.Error as e:
        logger.error("Error during payment fields migration: %s", e)
        # Don't raise exception - let the app continue with existing schema


def add_participant(participant_data: Dict) -> int:
    participant_data = _truncate_fields(participant_data)
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO participants
                (FullNameRU, Gender, Size, CountryAndCity, Church, Role, Department,
                 FullNameEN, SubmittedBy, ContactInformation, PaymentStatus, PaymentAmount, PaymentDate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    participant_data.get('FullNameRU'),
                    participant_data.get('Gender', 'F'),
                    participant_data.get('Size'),
                    participant_data.get('CountryAndCity'),
                    participant_data.get('Church'),
                    participant_data.get('Role', 'CANDIDATE'),
                    participant_data.get('Department'),
                    participant_data.get('FullNameEN'),
                    participant_data.get('SubmittedBy'),
                    participant_data.get('ContactInformation'),
                    participant_data.get('PaymentStatus', 'Unpaid'),
                    participant_data.get('PaymentAmount', 0),
                    participant_data.get('PaymentDate', ''),
                ),
            )
            participant_id = cursor.lastrowid
            return participant_id
    except sqlite3.IntegrityError as e:
        logger.error("Validation error while adding participant: %s", e)
        raise ValidationError(str(e)) from e
    except sqlite3.Error as e:
        logger.error("Database error while adding participant: %s", e)
        raise BotException("Database error while adding participant") from e


def get_all_participants() -> List[Dict]:
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM participants ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error("Database error while fetching participants: %s", e)
        raise BotException("Database error while fetching participants") from e


def get_participant_by_id(participant_id: int) -> Optional[Dict]:
    """
    ✅ ИСПРАВЛЕНО: возвращает None вместо исключения, если участник не найден.

    Args:
        participant_id: ID участника для поиска

    Returns:
        Dict с данными участника или None, если не найден

    Raises:
        BotException: При ошибках базы данных (но НЕ при "не найдено")
    """
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM participants WHERE id = ?",
                (participant_id,),
            )
            row = cursor.fetchone()
            if not row:
                logger.debug(f"Participant with id {participant_id} not found")
                return None
            return dict(row)
    except sqlite3.Error as e:
        logger.error(
            "Database error while fetching participant by ID %s: %s",
            participant_id,
            e,
        )
        raise BotException("Database error while fetching participant") from e


def get_participant_by_id_safe(participant_id: int, context: str = "") -> Optional[Dict]:
    """
    ✅ НОВАЯ ФУНКЦИЯ: безопасное получение участника с контекстным логированием.

    Args:
        participant_id: ID участника
        context: Контекст вызова для логирования (например, "update_participant")

    Returns:
        Dict с данными участника или None
    """
    participant = get_participant_by_id(participant_id)
    if participant is None:
        logger.warning(
            f"Participant {participant_id} not found in context: {context or 'unknown'}"
        )
    else:
        logger.debug(
            f"Found participant {participant_id} ({participant.get('FullNameRU', 'unnamed')}) "
            f"in context: {context or 'unknown'}"
        )
    return participant


def update_participant(participant_id: int, participant_data: Dict) -> bool:
    """Update a participant or raise ParticipantNotFoundError if missing."""

    participant_data = _truncate_fields(participant_data)
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE participants SET
                FullNameRU = ?, Gender = ?, Size = ?, CountryAndCity = ?, Church = ?,
                Role = ?, Department = ?, FullNameEN = ?, SubmittedBy = ?,
                ContactInformation = ?, PaymentStatus = ?, PaymentAmount = ?, PaymentDate = ?, 
                updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    participant_data.get('FullNameRU'),
                    participant_data.get('Gender', 'F'),
                    participant_data.get('Size'),
                    participant_data.get('CountryAndCity'),
                    participant_data.get('Church'),
                    participant_data.get('Role', 'CANDIDATE'),
                    participant_data.get('Department'),
                    participant_data.get('FullNameEN'),
                    participant_data.get('SubmittedBy'),
                    participant_data.get('ContactInformation'),
                    participant_data.get('PaymentStatus', 'Unpaid'),
                    participant_data.get('PaymentAmount', 0),
                    participant_data.get('PaymentDate', ''),
                    participant_id,
                ),
            )
            if cursor.rowcount == 0:
                raise ParticipantNotFoundError(
                    f"Participant with id {participant_id} not found"
                )
            return True
    except sqlite3.IntegrityError as e:
        logger.error("Validation error while updating participant %s: %s", participant_id, e)
        raise ValidationError(str(e)) from e
    except sqlite3.Error as e:
        logger.error("Database error while updating participant %s: %s", participant_id, e)
        raise BotException("Database error while updating participant") from e


def delete_participant(participant_id: int) -> bool:
    """
    ✅ НОВАЯ ФУНКЦИЯ: удаление участника по ID.

    Args:
        participant_id: ID участника для удаления

    Returns:
        bool: True если удаление успешно

    Raises:
        ParticipantNotFoundError: Если участник не найден
        BotException: При ошибках базы данных
    """
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM participants WHERE id = ?",
                (participant_id,),
            )

            if cursor.rowcount == 0:
                raise ParticipantNotFoundError(
                    f"Participant with id {participant_id} not found for deletion"
                )

            logger.info("Successfully deleted participant %s", participant_id)
            return True

    except sqlite3.Error as e:
        logger.error(
            "Database error while deleting participant %s: %s", participant_id, e
        )
        raise BotException("Database error while deleting participant") from e


VALID_FIELDS = {
    'FullNameRU', 'Gender', 'Size', 'CountryAndCity', 'Church',
    'Role', 'Department', 'FullNameEN', 'SubmittedBy', 'ContactInformation',
    'PaymentStatus', 'PaymentAmount', 'PaymentDate'
}


def _validate_participant_fields(field_updates: Dict) -> bool:
    """Check that provided fields are valid columns in the table."""
    if not field_updates:
        return False
    return all(field in VALID_FIELDS for field in field_updates.keys())


def update_participant_field(participant_id: int, field_updates: Dict) -> bool:
    """Update specific fields for a participant without touching other data."""

    if not _validate_participant_fields(field_updates):
        logger.error("Invalid fields for update: %s", list(field_updates.keys()))
        raise ValidationError("Invalid fields for update")

    field_updates = _truncate_fields(field_updates)
    set_clause = ", ".join(f"{field} = ?" for field in field_updates.keys())
    values = list(field_updates.values())
    values.append(participant_id)

    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            query = f"UPDATE participants SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            cursor.execute(query, values)
            if cursor.rowcount == 0:
                raise ParticipantNotFoundError(
                    f"Participant with id {participant_id} not found"
                )
            return True
    except sqlite3.IntegrityError as e:
        logger.error(
            "Validation error while updating fields for participant %s: %s",
            participant_id,
            e,
        )
        raise ValidationError(str(e)) from e
    except sqlite3.Error as e:
        logger.error(
            "Database error while updating fields for participant %s: %s",
            participant_id,
            e,
        )
        raise BotException("Database error while updating participant fields") from e


def find_participant_by_name(full_name_ru: str) -> Optional[Dict]:
    """Ищет участника по имени. Возвращает dict или None, если не найден."""
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM participants WHERE FullNameRU = ?",
                (full_name_ru,),
            )
            row = cursor.fetchone()
            # Если строка не найдена, просто возвращаем None. Это не ошибка.
            if not row:
                return None
            return dict(row)
    except sqlite3.Error as e:
        logger.error("Database error while searching participant: %s", e)
        # В случае реальной ошибки БД, мы по-прежнему генерируем исключение.
        raise BotException("Database error while searching participant") from e


def update_payment_status(participant_id: int, status: str, amount: int, date: str) -> bool:
    """
    Update payment status for a specific participant.
    
    Args:
        participant_id: ID of the participant
        status: Payment status (Unpaid, Paid, Partial, Refunded)
        amount: Payment amount in shekels (integer)
        date: Payment date in ISO format
        
    Returns:
        bool: True if update was successful
        
    Raises:
        ParticipantNotFoundError: If participant not found
        ValidationError: If validation fails
        BotException: On database errors
    """
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE participants SET
                PaymentStatus = ?, PaymentAmount = ?, PaymentDate = ?, 
                updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, amount, date, participant_id),
            )
            if cursor.rowcount == 0:
                raise ParticipantNotFoundError(
                    f"Participant with id {participant_id} not found"
                )
            logger.info(f"Updated payment for participant {participant_id}: {status}, {amount}₪")
            return True
    except sqlite3.IntegrityError as e:
        logger.error("Validation error while updating payment for participant %s: %s", participant_id, e)
        raise ValidationError(str(e)) from e
    except sqlite3.Error as e:
        logger.error("Database error while updating payment for participant %s: %s", participant_id, e)
        raise BotException("Database error while updating payment") from e


def get_unpaid_participants() -> List[Dict]:
    """
    Get all participants with unpaid status.
    
    Returns:
        List[Dict]: List of unpaid participants
        
    Raises:
        BotException: On database errors
    """
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM participants 
                WHERE PaymentStatus = 'Unpaid' 
                ORDER BY created_at DESC
                """
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error("Database error while fetching unpaid participants: %s", e)
        raise BotException("Database error while fetching unpaid participants") from e


def get_payment_summary() -> Dict:
    """
    Get payment summary statistics.
    
    Returns:
        Dict: Payment summary with counts and totals
        
    Raises:
        BotException: On database errors
    """
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            
            # Get counts by payment status
            cursor.execute(
                """
                SELECT PaymentStatus, COUNT(*) as count, SUM(PaymentAmount) as total
                FROM participants 
                GROUP BY PaymentStatus
                """
            )
            status_summary = {row[0]: {"count": row[1], "total": row[2] or 0} for row in cursor.fetchall()}
            
            # Get overall totals
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total_participants,
                    SUM(PaymentAmount) as total_amount,
                    COUNT(CASE WHEN PaymentStatus = 'Paid' THEN 1 END) as paid_count
                FROM participants
                """
            )
            row = cursor.fetchone()
            
            return {
                "status_breakdown": status_summary,
                "total_participants": row[0],
                "total_amount": row[1] or 0,
                "paid_count": row[2],
                "unpaid_count": row[0] - row[2]
            }
    except sqlite3.Error as e:
        logger.error("Database error while fetching payment summary: %s", e)
        raise BotException("Database error while fetching payment summary") from e


if __name__ == "__main__":
    init_database()
