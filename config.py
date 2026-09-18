import os
from pathlib import Path
from dotenv import load_dotenv

# Carica il file .env presente nella radice del progetto
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Token e credenziali Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Credenziali di invio email
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
CV_FILE_PATH = os.getenv("CV_FILE_PATH", "cv/curriculum.pdf")

# Percorso del database SQLite
DATABASE_PATH = BASE_DIR / "data" / "jobs.db"

# Parole chiave e località target per il filtraggio
TARGET_KEYWORDS = [
    "logopedista",
    "logopedia",
    "riabilitazione",
    "vocal coach",
    "disfonia"
    "deglutizione"
]

TARGET_LOCATIONS = [
    "firenze",
    "prato",
    "scandicci",
    "sesto fiorentino",
    "campi bisenzio",
    "empoli",
    "montelupo",
    "poggio a caiano",
    "carmignano"
]
