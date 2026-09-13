import os
import re
import hashlib
import sqlite3
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

SEARCHES = [
    "alternance BTS MCO commerce Bordeaux",
    "alternance BTS NDRC commerce Bordeaux",
    "alternance BTS MCO Saint André de Cubzac",
    "alternance BTS NDRC Saint André de Cubzac",
    "alternance BTS MCO Libourne",
    "alternance BTS NDRC Libourne",
    "alternance BTS MCO Blaye",
    "alternance BTS NDRC Blaye",
    "alternance BTS MCO Bruges Eysines Mérignac",
    "alternance BTS NDRC Bruges Eysines Mérignac",
]

DB = "seen.db"


def init_db():
    con = sqlite3.connect(DB)
    con.execute(
        "CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY)"
    )
    con.commit()
    return con


def search_web(query):
    url = (
        "https://html.duckduckgo.com/html/?q="
        + quote(query)
    )

    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    results = []

    for link in soup.select(".result__a"):
        href = link.get("href")
        title = link.get_text(" ", strip=True)

        if href and title:
            results.append((title, href))

    return results[:10]


def relevant(title, url):
    text = (title + " " + url).lower()

    alternance = (
        "alternance" in text
        or "apprentissage" in text
    )

    commerce = (
        "mco" in text
        or "ndrc" in text
        or "commerce" in text
        or "commercial" in text
        or "vendeur" in text
        or "conseiller" in text
    )

    return alternance and commerce


def clean_url(url):
    return re.sub(r"&rut=[^&]+", "", url)


def send_message(text):
    url = (
        f"https://api.telegram.org/bot"
        f"{BOT_TOKEN}/sendMessage"
    )

    response = requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": True,
        },
        timeout=20,
    )
print(response.text)
    response.raise_for_status()


def main():
    con = init_db()
    new_offers = []

    for query in SEARCHES:
        try:
            results = search_web(query)

            for title, url in results:
                url = clean_url(url)

                if not relevant(title, url):
                    continue

                offer_id = hashlib.sha256(
                    url.encode()
                ).hexdigest()

                already_seen = con.execute(
                    "SELECT 1 FROM seen WHERE id=?",
                    (offer_id,),
                ).fetchone()

                if already_seen:
                    continue

                con.execute(
                    "INSERT OR IGNORE INTO seen(id) VALUES(?)",
                    (offer_id,),
                )

                new_offers.append((title, url))

        except Exception as error:
            print(
                "Recherche échouée:",
                query,
                error,
            )

    con.commit()
    con.close()

    if not new_offers:
        send_message(
            "🔎 Pas de nouvelle annonce trouvée "
            "aujourd'hui pour BTS MCO/NDRC "
            "autour de Marsas/Bordeaux."
        )
        return

    header = (
        "🔎 NOUVELLES ALTERNANCES\n"
        "🎓 BTS MCO / BTS NDRC\n"
        "📍 Marsas → alentours → Bordeaux\n\n"
    )

    message = header

    for title, url in new_offers[:40]:
        item = (
            f"• {title}\n"
            f"🔗 {url}\n\n"
        )

        if len(message) + len(item) > 3800:
            send_message(message)
            message = ""

        message += item

    if message.strip():
        send_message(message)


if __name__ == "__main__":
    main()
