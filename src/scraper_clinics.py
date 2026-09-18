import re
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

import config
from src import database


TARGET_CLINICS: List[Dict[str, str]] = [
    {
        "name": "Istituto Prosperius",
        "location": "Firenze",
        "url": "https://www.prosperius.it/lavora-con-noi/"
    },
    {
        "name": "Rete PAS - Centri Medici",
        "location": "Firenze/Scandicci",
        "url": "https://www.retepas.org/lavora-con-noi/"
    },
    {
        "name": "Istituto Fanfani Ricerche Cliniche",
        "location": "Firenze",
        "url": "https://www.istitutofanfani.it/lavora-con-noi/"
    },
    {
        "name": "Villa Donatello",
        "location": "Sesto Fiorentino",
        "url": "https://villadonatello.com/lavora-con-noi/"
    },
    {
        "name": "Misericordia di Firenze",
        "location": "Firenze",
        "url": "https://www.misericordia.firenze.it/contatti"
    },
    {
        "name": "Misericordia di Prato",
        "location": "Prato",
        "url": "https://www.misericordia.prato.it/contatti/"
    }
]


def fetch_page_content(url: str) -> Optional[str]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.text
        print(f"[CLINICS] Risposta non valida da {url}: Codice {response.status_code}")
        return None
    except Exception as error:
        print(f"[CLINICS] Errore di connessione a {url}: {error}")
        return None


def extract_emails_from_html(html_text: str) -> Optional[str]:
    soup = BeautifulSoup(html_text, "html.parser")

    # 1. Priorità ai link espliciti <a href="mailto:...">
    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        if href.lower().startswith("mailto:"):
            email = href.replace("mailto:", "").split("?")[0].strip()
            if email:
                return email.lower()

    # 2. Ricerca regex nel testo con delimitazione sui TLD comuni
    text = soup.get_text(separator=" ", strip=True)
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.(?:it|com|org|net|eu)\b'
    match = re.search(email_pattern, text, re.IGNORECASE)
    if match:
        return match.group(0).lower()

    return None


def detect_logopedia_mentions(html_text: str) -> List[str]:
    soup = BeautifulSoup(html_text, "html.parser")
    text = soup.get_text(separator=" ", strip=True).lower()

    matched_keywords = []
    for keyword in config.TARGET_KEYWORDS:
        if keyword.lower() in text:
            matched_keywords.append(keyword)

    return matched_keywords


def run_clinics_scraper() -> List[int]:
    new_job_ids = []
    print(f"[CLINICS] Avvio scansione su {len(TARGET_CLINICS)} cliniche del territorio...")

    for clinic in TARGET_CLINICS:
        name = clinic["name"]
        url = clinic["url"]
        location = clinic["location"]

        html_content = fetch_page_content(url)
        if not html_content:
            continue

        matches = detect_logopedia_mentions(html_content)
        if matches:
            keywords_str = ", ".join(matches)
            title = f"Opportunità / Segnalazione Logopedista - {name}"
            description = (
                f"Trovati riferimenti a: {keywords_str} "
                f"nella sezione carriere/contatti di {name} ({location})."
            )
            contact_email = extract_emails_from_html(html_content)

            job_id = database.insert_job(
                source="LOCAL_CLINIC",
                external_id=url,
                title=title,
                company=name,
                location=location,
                url=url,
                description=description,
                contact_email=contact_email
            )

            if job_id is not None:
                new_job_ids.append(job_id)
                print(f"[CLINICA RILEVATA] #{job_id} {name} (Email: {contact_email})")

    print(f"[CLINICS] Scansione cliniche completata. Nuove opportunità registrate: {len(new_job_ids)}")
    return new_job_ids
