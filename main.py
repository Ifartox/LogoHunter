import sys
import asyncio
from src import database
from src.scraper_rss import run_rss_scraper
from src.scraper_clinics import run_clinics_scraper
from src.notifier import notify_new_jobs, start_interactive_listener
from src.mailer import process_approved_applications


async def run_pipeline_check() -> None:
    """
    Esegue il ciclo completo di aggiornamento:
    1. Inizializza il database SQLite locale.
    2. Scandaglia i Feed RSS pubblici (Opzione B).
    3. Scandaglia le pagine carriere delle cliniche di Firenze/Prato (Opzione C).
    4. Spedisce le notifiche Telegram per tutte le nuove posizioni scoperte.
    5. Invia le email di candidatura per le offerte autorizzate dall'utente.
    """
    print("=" * 65)
    print("JOB HUNTER LOGOPEDIA (FIRENZE & PRATO) - PIPELINE INTEGRATA")
    print("=" * 65)

    # 1. Inizializzazione DB
    database.initialize_database()

    # 2. Scraping Feed RSS
    new_rss_jobs = run_rss_scraper()

    # 3. Scraping Cliniche Locali
    new_clinic_jobs = run_clinics_scraper()

    total_new = len(new_rss_jobs) + len(new_clinic_jobs)
    print(f"[PIPELINE] Totale nuove opportunità registrate: {total_new}")

    # 4. Invio notifiche Telegram con tasti interattivi
    sent_notifications = await notify_new_jobs()
    print(f"[PIPELINE] Notifiche inviate a Telegram: {sent_notifications}")

    # 5. Inoltro email approvate
    sent_emails = process_approved_applications()
    print(f"[PIPELINE] Candidature trasmesse via email: {sent_emails}")
    print("=" * 65)


def main() -> None:
    """
    Punto di ingresso da terminale:
    - 'python main.py' per eseguire un ciclo di scansione e notifica.
    - 'python main.py listen' per tenere attivo il bot Telegram in ascolto dei clic.
    """
    if len(sys.argv) > 1 and sys.argv[1] == "listen":
        print("[MODALITA] Bot Telegram in ascolto per i comandi interattivi...")
        start_interactive_listener()
    else:
        asyncio.run(run_pipeline_check())


if __name__ == "__main__":
    main()
