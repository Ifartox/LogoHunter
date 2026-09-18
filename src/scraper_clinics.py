import re
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

import config
from src import database


# Lista di strutture sanitarie e centri riabilitativi di Firenze e Prato
# Puoi aggiungere o modificare gli URL inserendo le pagine "Lavora con noi" o "Contatti"
# Lista corretta e verificata di strutture sanitarie
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
        "url": "https://www.misericordia.firenze.it/it/contatti"
    },
    {
        "name": "Misericordia di Prato",
        "location": "Prato",
        "url": "https://www.misericordia.prato.it/contatti/"
    },
    {
        "name": "Centro Medico San Sebastiano",
        "location": "Prato",
        "url": "https://www.sansebastianoprato.it/lavora-con-noi/"
    }
]


def fetch_page_content(url: str) -> Optional[str]:
    """
    Effettua una richiesta HTTP GET per scaricare il codice HTML di una pagina.
    Usa un User-Agent standard per identificarsi correttamente come browser web.
    """
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
        else:
            print(f"[CLINICS] Risposta non valida da {url}: Codice {response.status_code}")
            return None
    except Exception as error:
        print(f"[CLINICS] Errore di connessione a {url}: {error}")
        return None


def extract_emails_from_html(html_text: str) -> Optional[str]:
    """
    Cerca indirizzi email sia nei link mailto: sia nel testo puro della pagina.
    Restituisce la prima email utile individuata.
    """
    soup = BeautifulSoup(html_text, "html.parser")

    # 1. Controllo dei tag <a href="mailto:...">
    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        if href.lower().startswith("mailto:"):
            email = href.replace("mailto:", "").split("?")[0].strip()
            if email:
                return email.lower()

    # 2. Ricerca tramite espressione regolare nel testo visibile
    text = soup.get_text()
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    match = re.search(email_pattern, text)
    if match:
        return match.group(0).lower()

    return None


def detect_logopedia_mentions(html_text: str) -> List[str]:
    """
    Scansiona il testo della pagina alla ricerca di parole chiave pertinenti.
    Restituisce la lista dei termini rilevati.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    text = soup.get_text(separator=" ", strip=True).lower()

    matched_keywords = []
    for keyword in config.TARGET_KEYWORDS:
        if keyword.lower() in text:
            matched_keywords.append(keyword)

    return matched_keywords


def run_clinics_scraper() -> List[int]:
    """
    Scansiona l'elenco dei centri medici configurati.
    Se rileva menzioni di posizioni aperte o parole chiave correlate,
    salva una voce nel database locale.
    Restituisce gli ID dei nuovi record salvati.
    """
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
            title = f"Posizione / Opportunità Logopedista - {name}"
            description = (
                f"Rilevate corrispondenze per: {keywords_str} "
                f"presso la pagina carriere di {name} ({location})."
            )
            contact_email = extract_emails_from_html(html_content)

            # L'ID esterno è l'URL della clinica per evitare inserimenti multipli
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

    print(f"[CLINICS] Scansione cliniche completata. Nuove opportunità: {len(new_job_ids)}")
    return new_job_ids
