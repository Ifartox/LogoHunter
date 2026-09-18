import sys
import asyncio
from src import database
from src.scraper_rss import run_rss_scraper
from src.scraper_clinics import run_clinics_scraper
from src.scraper_web import run_web_scraper
from src.scraper_social import run_social_scraper
from src.notifier import notify_new_jobs, start_interactive_listener


async def run_pipeline_check() -> None:
    """
    Pipeline completa:
    1. Inizializza il database SQLite.
    2. Scandaglia i Feed RSS.
    3. Scandaglia le Cliniche Locali.
    4. Scandaglia le Bacheche Web aperte.
    5. Scandaglia i canali Social (LinkedIn e canali aperti).
    6. Invia su Telegram tutte le nuove offerte trovate.
    """
    print("=" * 65)
    print("JOB HUNTER LOGOPEDIA - PIPELINE INTEGRATA SOCIAL & WEB")
    print("=" * 65)

    # 1. Inizializzazione Database
    database.initialize_database()

    # 2. Scansione Feed RSS
    new_rss = run_rss_scraper()

    # 3. Scansione Cliniche Locali
    new_clinics = run_clinics_scraper()

    # 4. Scansione Bacheche Web
    new_web = run_web_scraper()

    # 5. Scansione Canali Social (LinkedIn + Telegram)
    new_social = run_social_scraper()

    total_new = len(new_rss) + len(new_clinics) + len(new_web) + len(new_social)
    print(f"[PIPELINE] Totale nuove opportunità registrate: {total_new}")

    # 6. Invio notifiche Telegram per tutte le nuove offerte
    sent_notifications = await notify_new_jobs()
    print(f"[PIPELINE] Notifiche inviate a Telegram: {sent_notifications}")

    print("[PIPELINE] Invio email disattivato: modalità sola notifica attiva.")
    print("=" * 65)


def main() -> None:
    """
    Punto di ingresso del programma.
    """
    if len(sys.argv) > 1 and sys.argv[1] == "listen":
        print("[MODALITA] Bot Telegram in ascolto per interazioni...")
        start_interactive_listener()
    else:
        asyncio.run(run_pipeline_check())


if __name__ == "__main__":
    main()

 
