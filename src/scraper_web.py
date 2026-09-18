import re
import urllib.parse
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

import config
from src import database


def extract_email(text: str) -> Optional[str]:
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.(?:it|com|org|net|eu)\b'
    match = re.search(email_pattern, text, re.IGNORECASE)
    if match:
        return match.group(0).lower()
    return None


def fetch_html_safe(url: str) -> Optional[str]:
    session = requests.Session()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9",
        "Connection": "keep-alive"
    }
    try:
        response = session.get(url, headers=headers, timeout=12)
        if response.status_code == 200:
            return response.text
        print(f"[WEB_SCRAPER] Fonte non accessibile ({url}) - Codice HTTP: {response.status_code}")
        return None
    except Exception as error:
        print(f"[WEB_SCRAPER] Errore di connessione verso {url}: {error}")
        return None


def scrape_concorsi_sanita(keyword: str, province: str) -> List[Dict[str, Any]]:
    # Query sul portale bandi e avvisi del servizio sanitario
    query = f"{keyword} {province}"
    encoded = urllib.parse.quote_plus(query)
    target_url = f"https://www.concorsipubblici.com/concorsi/{encoded}.htm"

    html_content = fetch_html_safe(target_url)
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    found_jobs = []

    # Cerca elementi lista o link a bandi sanitari
    for link in soup.find_all("a", href=True):
        href = link["href"]
        text = link.get_text(strip=True)
        if "/concorso-" in href and any(kw in text.lower() for kw in config.TARGET_KEYWORDS):
            full_url = urllib.parse.urljoin(target_url, href)
            found_jobs.append({
                "source": "BANDI_SANITARI_WEB",
                "external_id": full_url,
                "title": text,
                "company": "Servizio Sanitario Regionale / ASL",
                "location": province.capitalize(),
                "url": full_url,
                "description": f"Bando/Avviso pubblico per logopedista reperito online ({province.capitalize()}).",
                "contact_email": None
            })

    return found_jobs


def run_web_scraper() -> List[int]:
    new_ids = []
    print("[WEB_SCRAPER] Avvio scansione bacheche aperte per Firenze e Prato...")

    targets = [
        ("logopedista", "firenze"),
        ("logopedista", "prato")
    ]

    for kw, city in targets:
        print(f"[WEB_SCRAPER] Ricerca annunci per: '{kw}' a '{city}'...")
        items = scrape_concorsi_sanita(kw, city)

        for item in items:
            inserted_id = database.insert_job(
                source=item["source"],
                external_id=item["external_id"],
                title=item["title"],
                company=item["company"],
                location=item["location"],
                url=item["url"],
                description=item["description"],
                contact_email=item["contact_email"]
            )

            if inserted_id is not None:
                new_ids.append(inserted_id)
                print(f"[WEB NUOVA OFFERTA] #{inserted_id} {item['title'][:55]}... ({item['location']})")

    print(f"[WEB_SCRAPER] Scansione completata. Nuovi annunci salvati: {len(new_ids)}")
    return new_ids
