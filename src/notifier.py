import html
import asyncio
from typing import Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
)

import config
from src import database


def build_job_card(job: dict) -> str:
    """
    Formatta i dati dell'annuncio in un messaggio leggibile con HTML.
    Esegue l'escape dei caratteri speciali per evitare errori di sintassi.
    """
    safe_title = html.escape(job.get("title", "Titolo non disponibile"))
    safe_company = html.escape(job.get("company", "Non specificata"))
    safe_location = html.escape(job.get("location", "Firenze/Prato"))
    safe_url = job.get("url", "")
    safe_email = html.escape(job.get("contact_email") or "Non rilevata")

    message_text = (
        f"🩺 <b>Nuova Opportunità per Logopedista</b>\n\n"
        f"📌 <b>Ruolo:</b> {safe_title}\n"
        f"🏢 <b>Struttura:</b> {safe_company}\n"
        f"📍 <b>Zona:</b> {safe_location}\n"
        f"✉️ <b>Email contatto:</b> {safe_email}\n"
        f"🔗 <b>Link:</b> <a href=\"{safe_url}\">Visualizza annuncio</a>\n\n"
        f"<i>Cosa desideri fare?</i>"
    )
    return message_text


def build_job_keyboard(job_id: int, url: str) -> InlineKeyboardMarkup:
    """
    Crea i pulsanti per la modalità sola notifica:
    - Un pulsante URL che apre direttamente il link dell'annuncio nel browser del telefono.
    - Un pulsante 'Archivia' per contrassegnare l'annuncio come letto.
    """
    keyboard = [
        [
            InlineKeyboardButton("🌐 Apri Annuncio", url=url),
            InlineKeyboardButton("📁 Archivia", callback_data=f"skip_{job_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def send_job_notification(app: Application, job: dict) -> bool:
    """
    Invia un singolo annuncio alla chat Telegram configurata.
    """
    chat_id = config.TELEGRAM_CHAT_ID
    if not chat_id:
        print("[NOTIFIER] Errore: TELEGRAM_CHAT_ID non configurato nel file .env.")
        return False

    text = build_job_card(job)
    keyboard = build_job_keyboard(job["id"])

    try:
        await app.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard,
            disable_web_page_preview=False
        )
        return True
    except Exception as error:
        print(f"[NOTIFIER] Errore nell'invio del messaggio per l'annuncio #{job['id']}: {error}")
        return False


async def notify_new_jobs() -> int:
    """
    Cerca nel database tutti gli annunci nello stato 'DISCOVERED',
    invia una notifica Telegram per ciascuno e ne aggiorna lo stato a 'NOTIFIED'.
    Restituisce il numero totale di notifiche inviate con successo.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[NOTIFIER] Token o Chat ID mancanti. Notifiche saltate.")
        return 0

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    await app.initialize()

    connection = database.get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM job_offers WHERE status = 'DISCOVERED'")
    pending_jobs = [dict(row) for row in cursor.fetchall()]
    connection.close()

    sent_count = 0
    for job in pending_jobs:
        success = await send_job_notification(app, job)
        if success:
            database.update_job_status(job["id"], "NOTIFIED")
            sent_count += 1
            # Piccola pausa per non saturare i limiti orari dell'API di Telegram
            await asyncio.sleep(1)

    await app.shutdown()
    return sent_count


async def handle_button_press(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gestisce l'evento di pressione dei pulsanti 'Invia CV' o 'Ignora' da Telegram.
    """
    query = update.callback_query
    await query.answer()

    data = query.data
    action, raw_id = data.split("_", 1)
    job_id = int(raw_id)

    job = database.get_job_by_id(job_id)
    if not job:
        await query.edit_message_text("❌ Annuncio non trovato nel database.")
        return

    if action == "send":
        # Segnamo lo stato pronto all'invio nel database
        database.update_job_status(job_id, "QUEUED_FOR_SENDING")
        await query.edit_message_text(
            f"✅ <b>Candidatura registrata</b> per: <i>{html.escape(job['title'])}</i>.\n"
            f"La procedura di inoltro email elaborerà l'invio.",
            parse_mode="HTML"
        )
    elif action == "skip":
        database.update_job_status(job_id, "SKIPPED")
        await query.edit_message_text(
            f"🗑️ Annuncio archiviato e ignorato: <i>{html.escape(job['title'])}</i>.",
            parse_mode="HTML"
        )


def start_interactive_listener() -> None:
    """
    Avvia il bot in modalità ascolto continuo (polling) per ricevere i clic sui pulsanti.
    Utile quando si esegue il bot localmente sul proprio computer.
    """
    if not config.TELEGRAM_BOT_TOKEN:
        print("[NOTIFIER] Impossibile avviare il listener: TELEGRAM_BOT_TOKEN non impostato.")
        return

    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CallbackQueryHandler(handle_button_press))

    print("[NOTIFIER] Bot in ascolto per i comandi Human-in-the-loop (Ctrl+C per fermare)...")
    application.run_polling()
