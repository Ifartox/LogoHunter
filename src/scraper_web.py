from typing import List


def run_web_scraper() -> List[int]:
    """
    Modulo di scansione per bacheche web esterne.

    Scopo:
    Questo modulo è predisposto per accogliere future bacheche aperte.
    Al momento restituisce una lista vuota per evitare blocchi HTTP 403
    causati dai filtri anti-bot dei server cloud di GitHub Actions.

    Valore restituito:
    - List[int]: lista contenente gli ID degli annunci inseriti (attualmente vuota).
    """
    print("[WEB_SCRAPER] Scansione bacheche web esterne disattivata (in attesa di nuovi endpoint aperti).")
    return []
