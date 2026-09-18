import urllib.parse
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

import config
from src import database


def fetch_linkedin_public_jobs(keyword: str, location: str) -> List[Dict[str, Any]]:
    """
    Interroga l'endpoint pubblico 'jobs-guest' di LinkedIn.
    Non richiede credenziali di accesso né browser pesanti.
    """
    encoded_kw = urllib.parse.quote(keyword)
    encoded_loc = urllib.parse.quote(location)

    # URL dell'interfaccia aperta per la visualizzazione delle offerte
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={encoded_kw}&location={encoded_loc}&start=0"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"[SOCIAL_SCRAPER] Risposta da LinkedIn ({location}): Codice {response.status_code}")
            return []
    except Exception as error:
        print(f"[SOCIAL_SCRAPER] Errore di connessione a LinkedIn per {location}: {error}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    found_jobs = []

    # Le schede degli annunci in LinkedIn sono contenute in tag <li>
    job_cards = soup.find_all("li")

    for card in job_cards:
        # Estrazione del titolo
        title_tag = card.find("h3", class_="base-search-card__title")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)

        # Estrazione dell'azienda/studio
        company_tag = card.find("h4", class_="base-search-card__subtitle")
        company = company_tag.get_text(strip=True) if company_tag else "Azienda su LinkedIn"

        # Estrazione della località
        loc_tag = card.find("span", class_="job-search-card__location")
        job_location = loc_tag.get_text(strip=True) if loc_tag else location.capitalize()

        # Estrazione del link dell'annuncio
        link_tag = card.find("a", class_="base-card__full-link", href=True)
        if not link_tag:
            continue
        job_url = link_tag["href"].split("?")[0]  # Rimuoviamo i parametri di tracciamento URL

        # Filtro di pertinenza: controlliamo che il titolo contenga le nostre parole chiave
        title_lower = title.lower()
        if not any(kw.lower() in title_lower for kw in config.TARGET_KEYWORDS):
            continue

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


def run_social_scraper() -> List[int]:
    """
    Coordina la ricerca di offerte per logopedisti su LinkedIn per Firenze e Prato.
    Salva le novità nel database ed evita i duplicati.
    """
    new_ids = []
    print("[SOCIAL_SCRAPER] Avvio scansione annunci social (LinkedIn) per Firenze e Prato...")

    targets = [
        ("logopedista", "Firenze"),
        ("logopedista", "Prato")
    ]

    for kw, city in targets:
        print(f"[SOCIAL_SCRAPER] Ricerca: '{kw}' a '{city}'...")
        jobs = fetch_linkedin_public_jobs(kw, city)

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
                print(f"[SOCIAL NUOVA OFFERTA] #{inserted_id} {item['title']} - {item['company']} ({item['location']})")

    print(f"[SOCIAL_SCRAPER] Scansione social completata. Nuovi annunci registrati: {len(new_ids)}")
    return new_ids
