#!/usr/bin/env python3
"""
Latvian Gas Station Price Scraper
Scrapes fuel prices from Circle K, Neste, Virši, and Viada
"""

import re
from urllib.request import urlopen, Request
from urllib.error import URLError


STATIONS = [
    {
        "name": "Circle K",
        "url": "https://www.circlek.lv/degviela-miles/degvielas-cenas",
        "color": "#E31837",
    },
    {
        "name": "Neste",
        "url": "https://www.neste.lv/lv/content/degvielas-cenas",
        "color": "#FF6600",
    },
    {
        "name": "Virši",
        "url": "https://www.virsi.lv/lv/privatpersonam/degviela/degvielas-un-elektrouzlades-cenas",
        "color": "#00963F",
    },
    {
        "name": "Viada",
        "url": "https://www.viada.lv/zemakas-degvielas-cenas/",
        "color": "#003087",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "lv,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_html(url):
    req = Request(url, headers=HEADERS)
    try:
        with urlopen(req, timeout=15) as resp:
            raw = resp.read()
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError:
                return raw.decode("latin-1")
    except URLError as e:
        print(f"  ERROR fetching {url}: {e}")
        return ""
    except Exception as e:
        print(f"  ERROR fetching {url}: {type(e).__name__}: {e}")
        return ""


# ── Fuel name normalisers ────────────────────────────────────────────────────

ALLOWED_FUELS = {"95", "98", "Diesel", "LPG"}

def normalise_fuel(raw):
    raw = raw.strip()
    low = raw.lower()
    if re.search(r"\bdmiles\b|\bfutura.?d\b|\bdd\b|neste futura d\b", low):
        return "Diesel"
    if re.search(r"95miles|futura.?95|futurama|95e|^95$", low):
        return "95"
    if re.search(r"98miles\+?|futura.?98|98e|^98$", low):
        return "98"
    if re.search(r"autogāze|lpg", low):
        return "LPG"
    return None


# ── Station-specific parsers ─────────────────────────────────────────────────

def parse_circlek(html):
    prices = {}
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I)
    for row in rows:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S | re.I)
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        cells = [c for c in cells if c]
        if len(cells) >= 2:
            m = re.search(r"(\d+\.\d+)", cells[1])
            if m and cells[0]:
                fuel = normalise_fuel(cells[0])
                if fuel and fuel in ALLOWED_FUELS and fuel not in prices:
                    prices[fuel] = float(m.group(1))
    return prices


def parse_neste(html):
    prices = {}
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I)
    for row in rows:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S | re.I)
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        cells = [c for c in cells if c]
        if len(cells) >= 2:
            m = re.search(r"(\d+\.\d+)", cells[1])
            if m and cells[0]:
                fuel = normalise_fuel(cells[0])
                if fuel and fuel in ALLOWED_FUELS and fuel not in prices:
                    prices[fuel] = float(m.group(1))
    return prices


def parse_virsi(html):
    prices = {}
    for keyword in ["DD", "95E", "98E", "LPG", "1.6", "1.7", "1.8"]:
        idx = html.lower().find(keyword.lower())
        if idx != -1:
            print(f"  DEBUG virsi '{keyword}' at {idx}: {html[max(0,idx-30):idx+60]!r}")
    pattern = re.compile(
        r"(DD|95E|98E|LPG)\s*\n?\s*([\d]+\.[\d]+)",
        re.I,
    )
    for m in pattern.finditer(html):
        fuel = normalise_fuel(m.group(1))
        price = float(m.group(2))
        if fuel and fuel in ALLOWED_FUELS and fuel not in prices:
            prices[fuel] = price
    return prices


def parse_viada(html):
    # Row indices (0-based, counting only rows that contain a price):
    # 0 = 95 Multi, 1 = 95 Multi X (skip), 2 = 98 Multi X,
    # 3 = D plain (skip), 4 = D Multi X, 5 = Gāze (LPG)
    ROW_MAP = {0: "95", 2: "98", 4: "Diesel", 5: "LPG"}
    prices = {}
    price_row_idx = 0

    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S | re.I)
        cells_clean = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]

        price_match = None
        for c in cells_clean:
            m = re.search(r"(\d+\.\d+)\s*EUR", c)
            if m:
                price_match = float(m.group(1))
                break

        if price_match is None:
            continue

        fuel_name = ROW_MAP.get(price_row_idx)
        if fuel_name:
            prices[fuel_name] = price_match
        price_row_idx += 1

    return prices


PARSERS = {
    "Circle K": parse_circlek,
    "Neste": parse_neste,
    "Virši": parse_virsi,
    "Viada": parse_viada,
}

# Fallback prices (manually scraped 2026-03-06) used when live fetch fails
def scrape_all():
    """Scrape all stations. Returns list of dicts with station info + prices."""
    results = []
    for station in STATIONS:
        name = station["name"]
        print(f"Fetching {name}...")
        html = fetch_html(station["url"])
        parser = PARSERS[name]
        prices = parser(html) if html else {}
        if not prices:
            print(f"  WARNING: Live fetch failed – skipping {name}")
        else:
            print(f"  Found {len(prices)} fuel types: {list(prices.keys())}")
        results.append({**station, "prices": prices, "cached": False})
    return results
