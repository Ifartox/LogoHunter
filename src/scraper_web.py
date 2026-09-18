import re
import urllib.parse
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

import config
from src import database


def extract_email(text: str) -> Optional[str]:
    """
    Cerca un indirizzo email all'interno del testo usando una Regular Expression (Regex).
    Restituisce l'email trovata in minuscolo, oppure None se non è presente.
    """
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    match = re.search(email_pattern, text)
    if match:
        return match.group(0).lower()
    return None


def fetch_html(url: str) -> Optional[str]:
    """
    Scarica il contenuto HTML di una pagina web tramite requests.
    Usa un 'User-Agent' per presentarsi come un normale browser ed evitare blocchi.
    """
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
        if response.status_code == 200:
            return response.text
        else:
            print(f"[WEB_SCRAPER] Pagina non raggiungibile ({url}) - Codice stato: {response.status_code}")
            return None
    except Exception as error:
        print(f"[WEB_SCRAPER] Errore di connessione verso {url}: {error}")
        return None


def scrape_open_job_board(keyword: str, city: str) -> List[Dict[str, Any]]:
    """
    Esegue la ricerca su una bacheca annunci aperta tramite parametri nell'URL.
    Estrae le informazioni strutturate (titolo, link, azienda, descrizione).
    """
    # Esempio su bacheca pubblica con parametri query puliti (es. MioDottore / portali sanitari aperti)
    encoded_kw = urllib.parse.quote(keyword)
    encoded_city = urllib.parse.quote(city)
    
    # URL di ricerca strutturato
    search_url = f"https://it.jooble.org/SearchResult?ukw={encoded_kw}&rgns={encoded_city}"
    
    html_content = fetch_html(search_url)
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    collected_jobs = []

    # Cerchiamo i contenitori degli annunci (i selettori possono variare in base al portale)
    # Cerchiamo tutti gli elementi che contengono link di lavoro
    job_cards = soup.find_all("article") or soup.find_all("div", attrs={"data-test-name": True})

    for card in job_cards:
        # Estraiamo il titolo o il link principale
        link_tag = card.find("a", href=True)
        if not link_tag:
            continue

        title = link_tag.get_text(separator=" ", strip=True)
        job_url = link_tag["href"]

        # Se il link è relativo (inizia con /), lo completiamo
        if job_url.startswith("/"):
            job_url = urllib.parse.urljoin(search_url, job_url)

        # Estraiamo il testo della descrizione della scheda
        description = card.get_text(separator=" ", strip=True)

        # Verifichiamo la presenza di una parola chiave valida
        title_lower = title.lower()
        if not any(kw in title_lower for kw in config.TARGET_KEYWORDS):
            continue

        # Estraiamo eventuale email di contatto dal testo
        contact_email = extract_email(description)

        collected_jobs.append({
            "source": "WEB_SCRAPER",
            "external_id": job_url,
            "title": title,
            "company": "Offerta Web",
            "location": city.capitalize(),
            "url": job_url,
            "description": description[:500],  # Limitiamo i primi 500 caratteri
            "contact_email": contact_email
        })

    return collected_jobs


def run_web_scraper() -> List[int]:
    """
    Funzione principale del modulo:
    1. Scansiona le combinazioni di parole chiave e città (Firenze, Prato).
    2. Registra i nuovi annunci trovati nel database SQLite.
    3. Restituisce gli ID dei record appena creati.
    """
    new_ids = []
    print("[WEB_SCRAPER] Avvio scansione bacheche web per Firenze e Prato...")

    # Termini mirati per la ricerca web
    keywords = ["logopedista"]
    cities = ["firenze", "prato"]

    for kw in keywords:
        for city in cities:
            print(f"[WEB_SCRAPER] Ricerca: '{kw}' a '{city}'...")
            jobs = scrape_open_job_board(kw, city)

            for item in jobs:
                # Salviamo nel database locale; se esiste già, restituisce None
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
                    print(f"[WEB NUOVA OFFERTA] #{inserted_id} {item['title'][:50]}... ({item['location']})")

    print(f"[WEB_SCRAPER] Scansione completata. Nuovi annunci web salvati: {len(new_ids)}")
    return new_ids
