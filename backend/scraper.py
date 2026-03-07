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


# ── Fuel name normalisers ────────────────────────────────────────────────────

def normalise_fuel(raw):
    raw = raw.strip()
    low = raw.lower()
    if re.search(r"\bdmiles\+\b|\bpro.?diesel\b|\bneste pro\b", low):
        return "Diesel Premium"
    if re.search(r"\bdmiles\b|\bfutura.?d\b|\bdd\b|\b95e.{0,3}dīzeļ|neste futura d\b", low):
        return "Diesel"
    if re.search(r"95miles|futura 95|95e|^95$", low):
        return "95"
    if re.search(r"98miles\+?|futura 98|98e|^98$", low):
        return "98"
    if re.search(r"autogāze|lpg", low):
        return "LPG"
    if re.search(r"cng", low):
        return "CNG"
    if re.search(r"adblue|adblū", low):
        return "AdBlue"
    if re.search(r"xtl|hvo|miles\+xtl", low):
        return "HVO/XTL"
    return raw


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
                if fuel not in prices:
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
                if fuel not in prices:
                    prices[fuel] = float(m.group(1))
    return prices


def parse_virsi(html):
    prices = {}
    pattern = re.compile(
        r"(DD|95E|98E|CNG|LPG|AdBLUE|AdBlue)\s*\n?\s*([\d]+\.[\d]+)",
        re.I,
    )
    for m in pattern.finditer(html):
        fuel = normalise_fuel(m.group(1))
        price = float(m.group(2))
        if fuel not in prices:
            prices[fuel] = price
    return prices


def parse_viada(html):
    prices = {}
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I)
    fuel_order = ["LPG", "Diesel", "95", "HVO/XTL", "98", "AdBlue", "CNG"]
    fuel_idx = 0

    for row in rows:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S | re.I)
        cells_clean = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        cells_raw = [c for c in cells]

        price_match = None
        for c in cells_clean:
            m = re.search(r"(\d+\.\d+)\s*EUR", c)
            if m:
                price_match = float(m.group(1))
                break

        if price_match is None:
            continue

        fuel_name = None
        for c in cells_raw:
            alt = re.search(r'alt=["\']([^"\']+)["\']', c, re.I)
            if alt:
                candidate = normalise_fuel(alt.group(1))
                if candidate:
                    fuel_name = candidate
                    break

        if not fuel_name and fuel_idx < len(fuel_order):
            fuel_name = fuel_order[fuel_idx]

        if fuel_name and fuel_name not in prices:
            prices[fuel_name] = price_match
        fuel_idx += 1

    return prices


PARSERS = {
    "Circle K": parse_circlek,
    "Neste": parse_neste,
    "Virši": parse_virsi,
    "Viada": parse_viada,
}

# Fallback prices (manually scraped 2026-03-06) used when live fetch fails
FALLBACK_PRICES = {
    "Circle K": {
        "95": 1.634,
        "98": 1.704,
        "Diesel": 1.694,
        "Diesel Premium": 1.804,
        "HVO/XTL": 2.370,
        "LPG": 0.925,
    },
    "Neste": {
        "95": 1.617,
        "98": 1.687,
        "Diesel": 1.677,
        "Diesel Premium": 1.807,
    },
    "Virši": {
        "Diesel": 1.677,
        "95": 1.627,
        "98": 1.697,
        "CNG": 1.425,
        "LPG": 0.925,
        "AdBlue": 0.845,
    },
    "Viada": {
        "LPG": 0.805,
        "Diesel": 1.592,
        "95": 1.537,
        "98": 1.512,
        "AdBlue": 1.684,
        "HVO/XTL": 1.959,
    },
}


def scrape_all():
    """Scrape all stations. Returns list of dicts with station info + prices."""
    results = []
    for station in STATIONS:
        name = station["name"]
        print(f"Fetching {name}...")
        html = fetch_html(station["url"])
        parser = PARSERS[name]
        prices = parser(html) if html else {}
        used_fallback = False
        if not prices:
            prices = FALLBACK_PRICES.get(name, {})
            used_fallback = True
            print(f"  WARNING: Live fetch failed – using fallback prices")
        print(f"  Found {len(prices)} fuel types: {list(prices.keys())}")
        results.append({**station, "prices": prices, "cached": used_fallback})
    return results
