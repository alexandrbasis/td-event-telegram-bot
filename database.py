import sqlite3
import logging
from typing import List, Dict, Optional

DB_PATH = "participants.db"
logger = logging.getLogger(__name__)


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
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                FullNameRU TEXT NOT NULL,
                Gender TEXT DEFAULT 'F',
                Size TEXT,
                CountryAndCity TEXT,
                Church TEXT,
                Role TEXT DEFAULT 'CANDIDATE',
                Department TEXT,
                FullNameEN TEXT,
                SubmittedBy TEXT,
                ContactInformation TEXT,
                roomId INTEGER,
                tableId INTEGER,
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
        conn.commit()
        print("✅ База данных инициализирована")
    except sqlite3.Error as e:
        logger.error("Database init error: %s", e)
    finally:
        if conn:
            conn.close()


def add_participant(participant_data: Dict) -> int:
    participant_data = _truncate_fields(participant_data)
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO participants
            (FullNameRU, Gender, Size, CountryAndCity, Church, Role, Department,
             FullNameEN, SubmittedBy, ContactInformation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )
        participant_id = cursor.lastrowid
        conn.commit()
        return participant_id
    except sqlite3.Error as e:
        logger.error("Failed to add participant: %s", e)
        return -1
    finally:
        if conn:
            conn.close()


def get_all_participants() -> List[Dict]:
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM participants ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error("Failed to fetch participants: %s", e)
        return []
    finally:
        if conn:
            conn.close()


def get_participant_by_id(participant_id: int) -> Optional[Dict]:
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM participants WHERE id = ?", (participant_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error("Failed to get participant: %s", e)
        return None
    finally:
        if conn:
            conn.close()


def update_participant(participant_id: int, participant_data: Dict) -> bool:
    participant_data = _truncate_fields(participant_data)
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE participants SET
            FullNameRU = ?, Gender = ?, Size = ?, CountryAndCity = ?, Church = ?,
            Role = ?, Department = ?, FullNameEN = ?, SubmittedBy = ?,
            ContactInformation = ?, updated_at = CURRENT_TIMESTAMP
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
                participant_id,
            ),
        )
        updated = cursor.rowcount > 0
        conn.commit()
        return updated
    except sqlite3.Error as e:
        logger.error("Failed to update participant: %s", e)
        return False
    finally:
        if conn:
            conn.close()


VALID_FIELDS = {
    'FullNameRU', 'Gender', 'Size', 'CountryAndCity', 'Church',
    'Role', 'Department', 'FullNameEN', 'SubmittedBy', 'ContactInformation'
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
        return False

    field_updates = _truncate_fields(field_updates)
    set_clause = ", ".join(f"{field} = ?" for field in field_updates.keys())
    values = list(field_updates.values())
    values.append(participant_id)

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        query = f"UPDATE participants SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        cursor.execute(query, values)
        updated = cursor.rowcount > 0
        conn.commit()
        return updated
    except sqlite3.Error as e:
        logger.error("Failed to update participant field(s): %s", e)
        return False
    finally:
        if conn:
            conn.close()


def find_participant_by_name(full_name_ru: str) -> Optional[Dict]:
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM participants WHERE FullNameRU = ?", (full_name_ru,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error("Failed to find participant: %s", e)
        return None
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    init_database()
