import re
import urllib.parse
from typing import List, Dict, Any, Optional
import feedparser
from bs4 import BeautifulSoup

import config
from src import database


# Parole che indicano articoli di cronaca, interviste o gossip (da SCARTARE)
EXCLUDE_KEYWORDS = [
    "condanna", "tribunale", "sentenza", "giudice", "processo",
    "cantare", "cantante", "canzone", "musica", "intervista",
    "polemica", "sindacato", "sciopero", "aggressione", "arresto"
]

# Parole che identificano una vera offerta o ricerca di personale (devono essere PRESENTI)
JOB_INDICATORS = [
    "cercasi", "cerca", "seleziona", "selezione", "assunzione", "assumiamo",
    "bando", "concorso", "avviso", "candidatura", "curriculum",
    "inserimento", "part-time", "full-time", "p.iva", "collaborazione",
    "studio", "centro", "clinica", "opportunità", "lavoro"
]


def clean_html(raw_html: str) -> str:
    """
    Rimuove i tag HTML dal testo della descrizione e restituisce testo semplice.
    """
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def extract_email(text: str) -> Optional[str]:
    """
    Estrae un indirizzo email dal testo usando un'espressione regolare.
    """
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    match = re.search(email_pattern, text)
    if match:
        return match.group(0).lower()
    return None


def is_relevant(title: str, description: str, location: str) -> bool:
    """
    Valuta con precisione se l'elemento è un vero annuncio di lavoro:
    1. Verifica che contenga la professione target (es. Logopedista).
    2. Verifica che contenga una località target (es. Firenze, Prato).
    3. Scarta se contiene parole di cronaca/gossip (Blacklist).
    4. Accetta se contiene indicatori di ricerca personale (Whitelist).
    """
    text_combined = f"{title} {description} {location}".lower()

    # 1. Controllo parola chiave della professione
    has_role = any(kw.lower() in text_combined for kw in config.TARGET_KEYWORDS)
    if not has_role:
        return False

    # 2. Controllo località geografica
    has_location = any(loc.lower() in text_combined for loc in config.TARGET_LOCATIONS)
    if not has_location:
        return False

    # 3. Filtro Blacklist: scarta se contiene termini di cronaca
    title_lower = title.lower()
    for bad_word in EXCLUDE_KEYWORDS:
        if bad_word in title_lower:
            print(f"[FILTRO SCARTATO] Articolo escluso per parola vietata '{bad_word}': {title[:50]}...")
            return False

    # 4. Filtro Whitelist: richiede almeno un termine tipico di offerta/ricerca lavoro
    has_job_signal = any(signal in text_combined for signal in JOB_INDICATORS)
    if not has_job_signal:
        print(f"[FILTRO SCARTATO] Nessun indicatore di assunzione rilevato: {title[:50]}...")
        return False

    return True


def build_feed_urls() -> List[str]:
    """
    Costruisce l'elenco degli indirizzi RSS da interrogare.
    Usa query mirate a bandi, assunzioni e ricerche aperte.
    """
    base_urls = []
    
    # Query più specifiche per annunci di lavoro
    queries = [
        "logopedista firenze cercasi OR assunzione OR bando",
        "logopedista prato cercasi OR assunzione OR bando",
        "logopedia firenze lavoro studio clinica",
        "logopedia prato lavoro studio clinica"
    ]

    for query in queries:
        encoded_query = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=it&gl=IT&ceid=IT:it"
        base_urls.append(url)

    return base_urls


def parse_feed(feed_url: str) -> List[Dict[str, Any]]:
    """
    Scarica e analizza un singolo Feed RSS.
    """
    parsed = feedparser.parse(feed_url)
    items = []

    for entry in parsed.entries:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        raw_description = entry.get("summary", "") or entry.get("description", "")
        clean_description = clean_html(raw_description)
        external_id = entry.get("id", link)

        company = entry.get("source", {}).get("title", "") if "source" in entry else ""
        if not company and "author" in entry:
            company = entry.get("author", "")

        contact_email = extract_email(clean_description)

        items.append({
            "source": "RSS_FEED",
            "external_id": external_id,
            "title": title,
            "company": company,
            "location": "Firenze/Prato",
            "url": link,
            "description": clean_description,
            "contact_email": contact_email
        })

    return items


def run_rss_scraper() -> List[int]:
    """
    Coordina la lettura di tutti gli indirizzi di feed RSS e applica i filtri.
    """
    feed_urls = build_feed_urls()
    new_job_ids = []

    print(f"[SCRAPER] Scansione di {len(feed_urls)} indirizzi Feed RSS in corso:")
    for idx, url in enumerate(feed_urls, 1):
        print(f"  --> Indirizzo {idx}: {url}")

    for url in feed_urls:
        try:
            entries = parse_feed(url)
            for item in entries:
                if not is_relevant(item["title"], item["description"], item["location"]):
                    continue

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
                    print(f"[OFFERTA VALIDA TROVATA] ID: {job_id} | {item['title'][:55]}...")

        except Exception as error:
            print(f"[ERRORE] Impossibile leggere il feed {url}: {error}")

    print(f"[SCRAPER] Scansione completata. Nuove offerte reali memorizzate: {len(new_job_ids)}")
    return new_job_ids
