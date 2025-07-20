import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

# Путь к файлу базы данных
DB_PATH = "participants.db"

def init_database():
    """Создание таблицы участников при первом запуске"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
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
    """)
    
    # Создаем индекс как в схеме
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS Candidates_index_0 
        ON participants (Size, Gender, FullNameRU, Department, Role)
    """)
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

def add_participant(participant_data: Dict) -> int:
    """Добавление нового участника"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO participants 
        (FullNameRU, Gender, Size, CountryAndCity, Church, Role, Department, 
         FullNameEN, SubmittedBy, ContactInformation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        participant_data.get('FullNameRU'),
        participant_data.get('Gender', 'F'),
        participant_data.get('Size'),
        participant_data.get('CountryAndCity'),
        participant_data.get('Church'),
        participant_data.get('Role', 'CANDIDATE'),
        participant_data.get('Department'),
        participant_data.get('FullNameEN'),
        participant_data.get('SubmittedBy'),
        participant_data.get('ContactInformation')
    ))
    
    participant_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return participant_id

def get_all_participants() -> List[Dict]:
    """Получение всех участников"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM participants ORDER BY created_at DESC")
    rows = cursor.fetchall()
    
    participants = [dict(row) for row in rows]
    conn.close()
    
    return participants

def get_participant_by_id(participant_id: int) -> Optional[Dict]:
    """Получение участника по ID"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM participants WHERE id = ?", (participant_id,))
    row = cursor.fetchone()
    
    conn.close()
    
    return dict(row) if row else None

def update_participant(participant_id: int, participant_data: Dict) -> bool:
    """Обновление данных участника"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE participants SET 
        FullNameRU = ?, Gender = ?, Size = ?, CountryAndCity = ?, Church = ?, 
        Role = ?, Department = ?, FullNameEN = ?, SubmittedBy = ?, 
        ContactInformation = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
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
        participant_id
    ))
    
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return updated

# Инициализация базы данных при импорте модуля
if __name__ == "__main__":
    init_database()

def find_participant_by_name(full_name_ru: str) -> Optional[Dict]:
    """Поиск участника по полному имени на русском"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM participants WHERE FullNameRU = ?", (full_name_ru,))
    row = cursor.fetchone()
    
    conn.close()
    
    return dict(row) if row else None