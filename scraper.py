"""
Dendermonde Nieuws Scraper
Haalt krantenkoppen op uit 4 bronnen en slaat ze op in SQLite.
"""

import sqlite3
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import hashlib
import os
import json

DB_PATH = "nieuws.db"

SOURCES = {
    "dender_journaal": {
        "name": "Dender Journaal",
        "type": "rss",
        "url": "https://denderjournaal.be/feed/",
        "filter": ["dendermonde", "baasrode", "grembergen", "schoonaarde",
                   "appels", "oudegem", "mespelare", "sint-gillis", "dender"]
    },
    "vrt_nws": {
        "name": "VRT NWS",
        "type": "scrape",
        "url": "https://www.vrt.be/vrtnws/nl/regio/oost-vlaanderen/dendermonde/",
        "filter": []
    },
    "hln": {
        "name": "HLN",
        "type": "scrape",
        "url": "https://www.hln.be/dendermonde",
        "filter": []
    },
    "stad_dendermonde": {
        "name": "Stad Dendermonde",
        "type": "scrape",
        "url": "https://www.dendermonde.be/nieuwsoverzicht",
        "filter": []
    }
}

THEMES = {
    "mobiliteit": ["verkeer", "werken", "fiets", "trein", "nmbs", "bus", "weg",
                   "kruispunt", "brug", "parking", "rijstrook", "infrabel"],
    "veiligheid": ["politie", "brand", "diefstal", "drugs", "arrest", "cel",
                   "rechtbank", "parket", "inbraak", "accident", "crash"],
    "politiek": ["gemeente", "stad", "burgemeester", "schepen", "gemeenteraad",
                 "bestuur", "budget", "beleid", "stemming", "verkiezingen"],
    "cultuur": ["museum", "festival", "concert", "tentoon", "kunst", "theater",
                "evenement", "feest", "erfgoed", "bibliotheek"],
    "sport": ["voetbal", "wielren", "zwem", "sport", "club", "kampioen",
              "tornooi", "frisbee", "basket", "tennis"],
    "natuur": ["dender", "water", "overstrom", "milieu", "groen", "park",
               "natuur", "klimaat", "rivier", "boom"],
    "economie": ["winkel", "bedrijf", "werk", "job", "ondernemer", "markt",
                 "apotheek", "handel", "investering", "project"]
}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS artikels (
            id TEXT PRIMARY KEY,
            bron TEXT,
            bron_naam TEXT,
            titel TEXT,
            url TEXT,
            datum TEXT,
            thema TEXT,
            toegevoegd TEXT
        )
    """)
    conn.commit()
    conn.close()


def make_id(titel, bron):
    return hashlib.md5(f"{bron}:{titel}".encode()).hexdigest()


def detect_theme(titel):
    titel_lower = titel.lower()
    scores = {}
    for thema, keywords in THEMES.items():
        score = sum(1 for kw in keywords if kw in titel_lower)
        if score > 0:
            scores[thema] = score
    if scores:
        return max(scores, key=scores.get)
    return "algemeen"


def is_relevant(titel, filter_words):
    if not filter_words:
        return True
    titel_lower = titel.lower()
    return any(w in titel_lower for w in filter_words)


def save_artikel(conn, bron_key, bron_naam, titel, url, datum):
    artikel_id = make_id(titel, bron_key)
    thema = detect_theme(titel)
    now = datetime.now(timezone.utc).isoformat()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO artikels
            (id, bron, bron_naam, titel, url, datum, thema, toegevoegd)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (artikel_id, bron_key, bron_naam, titel, url, datum, thema, now))
        return conn.execute("SELECT changes()").fetchone()[0]
    except Exception as e:
        print(f"  Fout bij opslaan: {e}")
        return 0


def scrape_rss(source_key, config):
    print(f"  RSS ophalen: {config['url']}")
    try:
        feed = feedparser.parse(config["url"])
        items = []
        for entry in feed.entries:
            titel = entry.get("title", "").strip()
            url = entry.get("link", "")
            datum = entry.get("published", datetime.now().isoformat())
            if is_relevant(titel, config["filter"]):
                items.append((titel, url, datum))
        print(f"  {len(items)} relevante artikels gevonden")
        return items
    except Exception as e:
        print(f"  Fout: {e}")
        return []


def scrape_vrt(config):
    print(f"  Scraping VRT NWS: {config['url']}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "nl-BE,nl;q=0.9",
        }
        r = requests.get(config["url"], headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/vrtnws/nl/20" not in href:
                continue
            titel = ""
            for tag in ["h2", "h3", "h4", "strong"]:
                el = a.find(tag)
                if el:
                    titel = el.get_text(strip=True)
                    break
            if not titel:
                titel = a.get_text(strip=True)
            if len(titel) < 20:
                continue
            url = f"https://www.vrt.be{href}" if href.startswith("/") else href
            datum = datetime.now(timezone.utc).isoformat()
            items.append((titel, url, datum))
        seen = set()
        unique = []
        for item in items:
            if item[0] not in seen:
                seen.add(item[0])
                unique.append(item)
        print(f"  {len(unique)} artikels gevonden")
        return unique
    except Exception as e:
        print(f"  Fout: {e}")
        return []


def scrape_hln(config):
    print(f"  Scraping HLN: {config['url']}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        }
        r = requests.get(config["url"], headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "hln.be" not in href and not href.startswith("/"):
                continue
            if "~a" not in href and "/a" not in href:
                continue
            titel_el = a.find(["h2", "h3", "h4"])
            if not titel_el:
                continue
            titel = titel_el.get_text(strip=True)
            if len(titel) < 15:
                continue
            url = href if href.startswith("http") else f"https://www.hln.be{href}"
            datum = datetime.now(timezone.utc).isoformat()
            items.append((titel, url, datum))
        seen = set()
        unique = []
        for item in items:
            if item[0] not in seen:
                seen.add(item[0])
                unique.append(item)
        print(f"  {len(unique)} koppen gevonden")
        return unique
    except Exception as e:
        print(f"  Fout: {e}")
        return []


def scrape_stad(config):
    print(f"  Scraping Stad Dendermonde: {config['url']}")
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; NieuwsBot/1.0)"}
        r = requests.get(config["url"], headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/nieuws/" not in href:
                continue
            titel = a.get_text(strip=True)
            if len(titel) < 15:
                continue
            url = href if href.startswith("http") else f"https://www.dendermonde.be{href}"
            datum = datetime.now(timezone.utc).isoformat()
            items.append((titel, url, datum))
        seen = set()
        unique = []
        for item in items:
            if item[0] not in seen:
                seen.add(item[0])
                unique.append(item)
        print(f"  {len(unique)} berichten gevonden")
        return unique
    except Exception as e:
        print(f"  Fout: {e}")
        return []


def write_stats():
    conn = sqlite3.connect(DB_PATH)
    thema_data = conn.execute("""
        SELECT thema, COUNT(*) as aantal FROM artikels
        WHERE datum >= date('now', '-30 days')
        GROUP BY thema ORDER BY aantal DESC
    """).fetchall()
    bron_data = conn.execute("""
        SELECT bron_naam, COUNT(*) as aantal FROM artikels
        WHERE datum >= date('now', '-30 days')
        GROUP BY bron_naam ORDER BY aantal DESC
    """).fetchall()
    recent = conn.execute("""
        SELECT titel, url, bron_naam, datum, thema FROM artikels
        ORDER BY toegevoegd DESC LIMIT 50
    """).fetchall()
    weekly = conn.execute("""
        SELECT strftime('%Y-W%W', toegevoegd) as week, COUNT(*) as aantal
        FROM artikels WHERE toegevoegd >= date('now', '-56 days')
        GROUP BY week ORDER BY week
    """).fetchall()
    stats = {
        "gegenereerd": datetime.now().isoformat(),
        "themas": [{"naam": r[0], "aantal": r[1]} for r in thema_data],
        "bronnen": [{"naam": r[0], "aantal": r[1]} for r in bron_data],
        "recent": [{"titel": r[0], "url": r[1], "bron": r[2], "datum": r[3], "thema": r[4]} for r in recent],
        "weekly": [{"week": r[0], "aantal": r[1]} for r in weekly]
    }
    os.makedirs("docs", exist_ok=True)
    with open("docs/stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    conn.close()
    print("stats.json geschreven naar docs/")


def run():
    print(f"\n=== Dendermonde Nieuws Scraper - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")
    init_db()
    conn = sqlite3.connect(DB_PATH)
    total_new = 0
    for source_key, config in SOURCES.items():
        print(f"[{config['name']}]")
        if config["type"] == "rss":
            items = scrape_rss(source_key, config)
        elif source_key == "vrt_nws":
            items = scrape_vrt(config)
        elif source_key == "hln":
            items = scrape_hln(config)
        elif source_key == "stad_dendermonde":
            items = scrape_stad(config)
        else:
            items = []
        new_count = 0
        for titel, url, datum in items:
            new_count += save_artikel(conn, source_key, config["name"], titel, url, datum)
        conn.commit()
        print(f"  {new_count} nieuwe artikels opgeslagen\n")
        total_new += new_count
    conn.close()
    print(f"=== Klaar: {total_new} nieuwe artikels toegevoegd ===\n")
    write_stats()


if __name__ == "__main__":
    run()
