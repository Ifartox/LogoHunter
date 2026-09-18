import re
import urllib.parse
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

import config
from src import database


def extract_email(text: str) -> Optional[str]:
    """
    Cerca un indirizzo email all'interno del testo usando una Regex.
    """
    pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.(?:it|com|org|net|eu)\b'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(0).lower()
    return None


def fetch_with_headers(url: str) -> Optional[str]:
    """
    Effettua una chiamata HTTP GET simulando una richiesta legittima da browser.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.text
        print(f"[SOCIAL] Errore di risposta da {url}: Codice {response.status_code}")
        return None
    except Exception as error:
        print(f"[SOCIAL] Connessione fallita verso {url}: {error}")
        return None


def is_location_valid(location_str: str) -> bool:
    """
    Verifica se la località appartiene alle province/città target (Firenze, Prato e limitrofi).
    Restituisce True se valida, False se appartiene ad altre province (es. Bologna).
    """
    loc_lower = location_str.lower()
    return any(target.lower() in loc_lower for target in config.TARGET_LOCATIONS)


# ---------------------------------------------------------------------------
# 1. SCRAPER PER LINKEDIN (Bacheca pubblica con filtro geografico)
# ---------------------------------------------------------------------------

def scrape_linkedin_jobs(keyword: str, location: str) -> List[Dict[str, Any]]:
    """
    Interroga la bacheca pubblica di LinkedIn filtrando solo per annunci
    effettivamente localizzati nelle zone target.
    """
    encoded_kw = urllib.parse.quote(keyword)
    encoded_loc = urllib.parse.quote(location)

    url = (
        f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
        f"keywords={encoded_kw}&location={encoded_loc}&start=0"
    )

    html_content = fetch_with_headers(url)
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    found_jobs = []
    job_cards = soup.find_all("li")

    for card in job_cards:
        # Estrazione del titolo
        title_elem = card.find("h3", class_="base-search-card__title")
        if not title_elem:
            continue
        title = title_elem.get_text(strip=True)

        # Controllo pertinenza professione
        title_lower = title.lower()
        if not any(kw.lower() in title_lower for kw in config.TARGET_KEYWORDS):
            continue

        # Estrazione della località rilevata dalla scheda
        location_elem = card.find("span", class_="job-search-card__location")
        job_location = location_elem.get_text(strip=True) if location_elem else location.capitalize()

        # FILTRO GEOGRAFICO STRINGENTE:
        # Se LinkedIn restituisce un annuncio fuori zona (es. Bologna, Roma), lo scartiamo
        if not is_location_valid(job_location):
            print(f"[SOCIAL FILTRO SCARTATO] Posizione non in target geografico ({job_location}): {title}")
            continue

        # Estrazione azienda
        company_elem = card.find("h4", class_="base-search-card__subtitle")
        company = company_elem.get_text(strip=True) if company_elem else "Struttura su LinkedIn"

        # Estrazione URL pulito
        link_elem = card.find("a", class_="base-card__full-link", href=True)
        if not link_elem:
            continue
        job_url = link_elem["href"].split("?")[0]

        found_jobs.append({
            "source": "LINKEDIN_JOBS",
            "external_id": job_url,
            "title": title,
            "company": company,
            "location": job_location,
            "url": job_url,
            "description": f"Offerta pubblicata su LinkedIn da {company} ({job_location}).",
            "contact_email": None
        })

    return found_jobs


# ---------------------------------------------------------------------------
# 2. SCRAPER PER CANALI TELEGRAM APERTI
# ---------------------------------------------------------------------------

PUBLIC_TELEGRAM_CHANNELS = [
    "concorsisanitari",
    "lavorotoscana"
]

def scrape_telegram_public_channel(channel_name: str) -> List[Dict[str, Any]]:
    """
    Legge la bacheca pubblica di un canale Telegram.
    """
    url = f"https://t.me/s/{channel_name}"
    html_content = fetch_with_headers(url)
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    messages = soup.find_all("div", class_="tgme_widget_message_wrap")
    found_jobs = []

    for msg in messages:
        text_elem = msg.find("div", class_="tgme_widget_message_text")
        if not text_elem:
            continue
        text = text_elem.get_text(separator=" ", strip=True)
        text_lower = text.lower()

        has_role = any(kw.lower() in text_lower for kw in config.TARGET_KEYWORDS)
        has_location = any(loc.lower() in text_lower for loc in config.TARGET_LOCATIONS)

        if not (has_role and has_location):
            continue

        link_elem = msg.find("a", class_="tgme_widget_message_date", href=True)
        message_url = link_elem["href"] if link_elem else url
        email = extract_email(text)

        first_line = text.split("\n")[0][:80]
        title = f"Post Social ({channel_name}): {first_line}"

        found_jobs.append({
            "source": f"TELEGRAM_CHANNEL_{channel_name.upper()}",
            "external_id": message_url,
            "title": title,
            "company": f"Canale Social @{channel_name}",
            "location": "Firenze/Prato",
            "url": message_url,
            "description": text[:500],
            "contact_email": email
        })

    return found_jobs


# ---------------------------------------------------------------------------
# FUNZIONE PRINCIPALE DEL MODULO
# ---------------------------------------------------------------------------

def run_social_scraper() -> List[int]:
    new_ids = []
    print("[SOCIAL_SCRAPER] Avvio scansione social (LinkedIn + Canali Lavoro Sanità)...")

    targets = [
        ("logopedista", "Firenze"),
        ("logopedista", "Prato")
    ]

    for kw, city in targets:
        print(f"[SOCIAL_SCRAPER] LinkedIn: ricerca '{kw}' a '{city}'...")
        jobs = scrape_linkedin_jobs(kw, city)
        for item in jobs:
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
                print(f"[SOCIAL NUOVO] #{inserted_id} {item['title']} - {item['company']} ({item['location']})")

    for channel in PUBLIC_TELEGRAM_CHANNELS:
        print(f"[SOCIAL_SCRAPER] Monitoraggio canale social @{channel}...")
        channel_jobs = scrape_telegram_public_channel(channel)
        for item in channel_jobs:
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
                print(f"[SOCIAL NUOVO] #{inserted_id} {item['title']} ({item['location']})")

    print(f"[SOCIAL_SCRAPER] Scansione social completata. Nuove offerte trovate: {len(new_ids)}")
    return new_ids
