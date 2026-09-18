import re
import urllib.parse
from typing import List, Dict, Any, Optional
import feedparser
from bs4 import BeautifulSoup

import config
from src import database


def clean_html(raw_html: str) -> str:
    """
    Rimuove i tag HTML dal testo della descrizione e restituisce testo semplice.
    Se il testo è vuoto, restituisce una stringa vuota.
    """
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    # Estrae solo il testo visibile separando i blocchi con uno spazio
    return soup.get_text(separator=" ", strip=True)


def extract_email(text: str) -> Optional[str]:
    """
    Cerca un indirizzo email all'interno di un testo non strutturato
    utilizzando un'espressione regolare standard (Regex).
    Restituisce la prima email trovata o None se non ne trova.
    """
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    match = re.search(email_pattern, text)
    if match:
        return match.group(0).lower()
    return None


def is_relevant(title: str, description: str, location: str) -> bool:
    """
    Controlla se l'annuncio contiene almeno una delle parole chiave del profilo
    (es. 'fisioterapista') e appartiene a una delle località target (Firenze, Prato, ecc.).
    """
    combined_text = f"{title} {description} {location}".lower()

    # Verifica presenza di almeno una parola chiave professionale
    has_keyword = any(kw.lower() in combined_text for kw in config.TARGET_KEYWORDS)

    # Verifica presenza di almeno una località target
    has_location = any(loc.lower() in combined_text for loc in config.TARGET_LOCATIONS)

    return has_keyword and has_location


def build_feed_urls() -> List[str]:
    """
    Costruisce l'elenco degli URL dei feed RSS da interrogare.
    Combina le parole chiave principali con le zone geografiche di interesse.
    
    Nota: usiamo feed aperti come Google Alerts / feed aggregatori pubblici
    che generano output RSS leggibili senza necessità di login.
    """
    base_urls = []
    
    # Esempio di combinazioni query per Google Alerts RSS o feed aperti
    # Sintassi URL feed Google News / Job query aperte:
    for keyword in ["logopedista", "logopedia"]:
        for city in ["firenze", "prato"]:
            query = f"{keyword} {city} lavoro"
            encoded_query = urllib.parse.quote(query)
            
            # Feed pubblico di Google News / Notizie lavoro
            url = f"https://news.google.com/rss/search?q={encoded_query}&hl=it&gl=IT&ceid=IT:it"
            base_urls.append(url)

    return base_urls


def parse_feed(feed_url: str) -> List[Dict[str, Any]]:
    """
    Effettua la lettura e il parsing di un singolo URL di feed RSS.
    Restituisce una lista di annunci strutturati come dizionari Python.
    """
    parsed = feedparser.parse(feed_url)
    items = []

    for entry in parsed.entries:
        # Recupero dei campi principali del feed
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        raw_description = entry.get("summary", "") or entry.get("description", "")
        clean_description = clean_html(raw_description)

        # L'ID esterno univoco: usiamo entry.id se disponibile, altrimenti il link
        external_id = entry.get("id", link)

        # Cerchiamo l'autore o la fonte dell'annuncio
        company = entry.get("source", {}).get("title", "") if "source" in entry else ""
        if not company and "author" in entry:
            company = entry.get("author", "")

        # Località desunta dal titolo o impostata di default sull'area coperta
        location = "Firenze/Prato"

        # Tentativo di estrarre un'email di contatto dalla descrizione
        contact_email = extract_email(clean_description)

        items.append({
            "source": "RSS_FEED",
            "external_id": external_id,
            "title": title,
            "company": company,
            "location": location,
            "url": link,
            "description": clean_description,
            "contact_email": contact_email
        })

    return items


def run_rss_scraper() -> List[int]:
    """
    Funzione principale del modulo:
    1. Recupera gli annunci da tutti i feed configurati.
    2. Valuta la pertinenza con i filtri.
    3. Inserisce gli annunci nel database SQLite.
    4. Restituisce la lista degli ID dei nuovi annunci memorizzati.
    """
    feed_urls = build_feed_urls()
    new_job_ids = []

    print(f"[SCRAPER] Avvio scansione su {len(feed_urls)} sorgenti RSS...")

    for url in feed_urls:
        try:
            entries = parse_feed(url)
            for item in entries:
                # Controlliamo la pertinenza dell'annuncio
                if not is_relevant(item["title"], item["description"], item["location"]):
                    continue

                # Inseriamo nel database (se già presente, insert_job restituisce None)
                job_id = database.insert_job(
                    source=item["source"],
                    external_id=item["external_id"],
                    title=item["title"],
                    company=item["company"],
                    location=item["location"],
                    url=item["url"],
                    description=item["description"],
                    contact_email=item["contact_email"]
                )

                if job_id is not None:
                    new_job_ids.append(job_id)
                    print(f"[NUOVO ANNUNCIO] ID: {job_id} | Titolo: {item['title'][:50]}...")

        except Exception as error:
            print(f"[ERRORE] Impossibile elaborare il feed {url}: {error}")

    print(f"[SCRAPER] Scansione completata. Trovati {len(new_job_ids)} nuovi annunci.")
    return new_job_ids
