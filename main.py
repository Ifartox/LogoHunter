import sys
import asyncio
from src import database
from src.scraper_rss import run_rss_scraper
from src.scraper_clinics import run_clinics_scraper
from src.scraper_web import run_web_scraper
from src.notifier import notify_new_jobs, start_interactive_listener


async def run_pipeline_check() -> None:
    """
    Esegue il ciclo completo di aggiornamento (Feed RSS + Cliniche + Web Scraper):
    1. Inizializza il database SQLite locale.
    2. Scandaglia i Feed RSS pubblici (Opzione B).
    3. Scandaglia le pagine carriere delle cliniche locali (Opzione C).
    4. Scandaglia le bacheche web aperte tramite il nuovo Web Scraper.
    5. Invia su Telegram tutte le nuove offerte scoperte.
    """
    print("=" * 65)
    print("JOB HUNTER LOGOPEDIA - PIPELINE INTEGRATA CON WEB SCRAPER")
    print("=" * 65)

    # 1. Inizializzazione Database
    database.initialize_database()

    # 2. Scansione Feed RSS
    new_rss_jobs = run_rss_scraper()

    # 3. Scansione Cliniche Locali
    new_clinic_jobs = run_clinics_scraper()

    # 4. Scansione Web Scraper
    new_web_jobs = run_web_scraper()

    total_new = len(new_rss_jobs) + len(new_clinic_jobs) + len(new_web_jobs)
    print(f"[PIPELINE] Totale nuove opportunità registrate: {total_new}")

    # 5. Invio notifiche Telegram per tutte le nuove offerte trovate
    sent_notifications = await notify_new_jobs()
    print(f"[PIPELINE] Notifiche inviate a Telegram: {sent_notifications}")

    print("[PIPELINE] Invio email disattivato: modalità sola notifica attiva.")
    print("=" * 65)


def main() -> None:
    """
    Punto di ingresso da riga di comando.
    """
    if len(sys.argv) > 1 and sys.argv[1] == "listen":
        print("[MODALITA] Bot Telegram in ascolto per interazioni...")
        start_interactive_listener()
    else:
        asyncio.run(run_pipeline_check())


if __name__ == "__main__":
    main()
