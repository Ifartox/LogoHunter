import re
import urllib.parse
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

import config
from src import database


def extract_email(text: str) -> Optional[str]:
    """
    Estrae un indirizzo email dal testo tramite un'espressione regolare (regex).
    """
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    match = re.search(email_pattern, text)
    if match:
        return match.group(0).lower()
    return None


def fetch_html_safe(url: str) -> Optional[str]:
    """
    Scarica il contenuto HTML configurando una sessione HTTP completa di header
    per ridurre il rischio di rifiuti 403/anti-bot.
    """
    session = requests.Session()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/",
        "DNT": "1",
        "Connection": "keep-alive"
    }
    try:
        response = session.get(url, headers=headers, timeout=12)
        if response.status_code == 200:
            return response.text
        else:
            print(f"[WEB_SCRAPER] Fonte non accessibile ({url}) - Codice HTTP: {response.status_code}")
            return None
    except Exception as error:
        print(f"[WEB_SCRAPER] Errore di connessione verso {url}: {error}")
        return None


def scrape_open_bacheca(keyword: str, city: str) -> List[Dict[str, Any]]:
    """
    Interroga portali pubblici di annunci/concorsi aperti per la Toscana.
    """
    query = f"{keyword} {city}"
    encoded_query = urllib.parse.quote(query)
    
    # Portale aggregatore aperto per la sanità regionale e concorsi/avvisi
    target_url = f"https://www.concorsipubblici.com/ricerca?search_api_views_fulltext={encoded_query}"

    html_content = fetch_html_safe(target_url)
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    found_jobs = []

    # Seleziona gli elementi che contengono le righe dei bandi o degli annunci
    job_rows = soup.find_all("div", class_="views-row")

    for row in job_rows:
        link_tag = row.find("a", href=True)
        if not link_tag:
            continue

        title = link_tag.get_text(separator=" ", strip=True)
        full_url = urllib.parse.urljoin("https://www.concorsipubblici.com", link_tag["href"])
        description = row.get_text(separator=" ", strip=True)

        # Verifica presenza della parola chiave e della località
        text_to_check = f"{title} {description}".lower()
        if keyword.lower() not in text_to_check:
            continue

        contact_email = extract_email(description)

        found_jobs.append({
            "source": "CONCORSI_AVVISI_WEB",
            "external_id": full_url,
            "title": title,
            "company": "Ente Pubblico / Struttura Sanitaria",
            "location": city.capitalize(),
            "url": full_url,
            "description": description[:500],
            "contact_email": contact_email
        })

    return found_jobs


def run_web_scraper() -> List[int]:
    """
    Funzione principale del modulo:
    1. Scandaglia le ricerche per le province di Firenze e Prato.
    2. Salva nel database SQLite gli annunci non ancora censiti.
    3. Restituisce gli ID delle nuove posizioni inserite.
    """
    new_ids = []
    print("[WEB_SCRAPER] Avvio scansione bacheche aperte per Firenze e Prato...")

    targets = [
        ("logopedista", "firenze"),
        ("logopedista", "prato")
    ]

    for kw, city in targets:
        print(f"[WEB_SCRAPER] Ricerca annunci per: '{kw}' a '{city}'...")
        items = scrape_open_bacheca(kw, city)

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
