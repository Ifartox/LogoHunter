import sys
import asyncio
from src import database
from src.scraper_rss import run_rss_scraper
from src.scraper_clinics import run_clinics_scraper
from src.notifier import notify_new_jobs, start_interactive_listener
# Il modulo mailer al momento non serve, lo commentiamo per sicurezza:
# from src.mailer import process_approved_applications


async def run_pipeline_check() -> None:
    """
    Esegue il ciclo di aggiornamento in MODALITÀ SOLA NOTIFICA:
    1. Inizializza il database SQLite locale.
    2. Scandaglia i Feed RSS pubblici.
    3. Scandaglia le pagine carriere delle cliniche locali.
    4. Spedisce le notifiche con le offerte trovate sul tuo Telegram.
    (L'invio delle email è temporaneamente disattivato).
    """
    print("=" * 65)
    print("JOB HUNTER LOGOPEDIA - MODALITÀ MONITORAGGIO (SOLO TELEGRAM)")
    print("=" * 65)

    # 1. Inizializzazione del Database
    database.initialize_database()

    # 2. Scansione Feed RSS
    new_rss_jobs = run_rss_scraper()

    # 3. Scansione Cliniche Locali
    new_clinic_jobs = run_clinics_scraper()

    total_new = len(new_rss_jobs) + len(new_clinic_jobs)
    print(f"[PIPELINE] Totale nuove opportunità registrate: {total_new}")

    # 4. Invio notifiche su Telegram
    sent_notifications = await notify_new_jobs()
    print(f"[PIPELINE] Notifiche inviate a Telegram: {sent_notifications}")

    # 5. INVIO EMAIL DISATTIVATO TEMPORANEAMENTE
    # Nessuna email o CV verrà trasmesso.
    print("[PIPELINE] Invio email disattivato: modalità sola notifica attiva.")
    print("=" * 65)


def main() -> None:
    """
    Punto di ingresso da terminale.
    """
    if len(sys.argv) > 1 and sys.argv[1] == "listen":
        print("[MODALITA] Bot Telegram in ascolto per interazioni...")
        start_interactive_listener()
    else:
        asyncio.run(run_pipeline_check())


if __name__ == "__main__":
    main()
