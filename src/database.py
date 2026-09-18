import sqlite3
from typing import Optional, Dict, Any
from pathlib import Path
import config

def get_connection() -> sqlite3.Connection:
    """
    Crea e restituisce una connessione al database SQLite locale.
    Se la cartella di destinazione non esiste, viene creata automaticamente.
    """
    db_path = Path(config.DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    return connection

def initialize_database() -> None:
    """
    Crea la tabella per gli annunci di lavoro se non è già presente.
    Memorizza lo stato di lavorazione (scoperto, notificato, inviato, ignorato).
    """
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            external_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            company TEXT,
            location TEXT,
            url TEXT NOT NULL,
            description TEXT,
            contact_email TEXT,
            status TEXT DEFAULT 'DISCOVERED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    connection.commit()
    connection.close()

def job_exists(external_id: str) -> bool:
    """
    Verifica se un annuncio con un determinato identificatore esterno
    è già stato registrato nel database.
    """
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT 1 FROM job_offers WHERE external_id = ?", (external_id,))
    row = cursor.fetchone()
    connection.close()
    return row is not None

def insert_job(
    source: str,
    external_id: str,
    title: str,
    company: str,
    location: str,
    url: str,
    description: str,
    contact_email: Optional[str] = None
) -> Optional[int]:
    """
    Inserisce un nuovo annuncio nel database con stato iniziale 'DISCOVERED'.
    Restituisce l'identificativo numerico del record inserito oppure None se già presente.
    """
    if job_exists(external_id):
        return None

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO job_offers (
            source, external_id, title, company, location, url, description, contact_email, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'DISCOVERED')
    """, (source, external_id, title, company, location, url, description, contact_email))
    inserted_id = cursor.lastrowid
    connection.commit()
    connection.close()
    return inserted_id

def update_job_status(job_id: int, new_status: str) -> None:
    """
    Aggiorna lo stato di un annuncio (es. 'NOTIFIED', 'SENT', 'SKIPPED').
    """
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE job_offers SET status = ? WHERE id = ?", (new_status, job_id))
    connection.commit()
    connection.close()

def get_job_by_id(job_id: int) -> Optional[Dict[str, Any]]:
    """
    Recupera tutti i dati di un annuncio partendo dal suo ID numerico.
    """
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM job_offers WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    connection.close()
    if row:
        return dict(row)
    return None
