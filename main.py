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
    Esegue il ciclo completo di aggiornamento:
    1. Inizializza il database SQLite locale.
    2. Scandaglia i Feed RSS (Opzione B).
    3. Scandaglia le pagine delle cliniche (Opzione C).
    4. Scandaglia le bacheche web.
    5. Scandaglia i social network per il lavoro (LinkedIn).
    6. Invia notifiche Telegram per ogni nuova posizione registrata.
    """
    print("=" * 65)
    print("JOB HUNTER LOGOPEDIA - PIPELINE INTEGRATA COMPLETA")
    print("=" * 65)

    # 1. Inizializzazione Database
    database.initialize_database()

    # 2. Scansione Feed RSS
    new_rss = run_rss_scraper()

    # 3. Scansione Cliniche Locali
    new_clinics = run_clinics_scraper()

    # 4. Scansione Web Scraper
    new_web = run_web_scraper()

    # 5. Scansione Social (LinkedIn)
    new_social = run_social_scraper()

    total_new = len(new_rss) + len(new_clinics) + len(new_web) + len(new_social)
    print(f"[PIPELINE] Totale nuove opportunità registrate: {total_new}")

    # 6. Invio notifiche Telegram
    sent_notifications = await notify_new_jobs()
    print(f"[PIPELINE] Notifiche inviate a Telegram: {sent_notifications}")

    print("[PIPELINE] Invio email disattivato: modalità sola notifica attiva.")
    print("=" * 65)


def main() -> None:
    """
    Punto di ingresso principale.
    """
    if len(sys.argv) > 1 and sys.argv[1] == "listen":
        print("[MODALITA] Bot Telegram in ascolto per interazioni...")
        start_interactive_listener()
    else:
        asyncio.run(run_pipeline_check())


if __name__ == "__main__":
    main()
