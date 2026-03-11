import re
import sys
import json
import time
import argparse
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path

from html import escape as html_escape
from urllib.parse import urlparse

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
GEOCACHE_FILE = BASE_DIR / 'geocache.json'

ALLOWED_URL_SCHEMES = {'http', 'https'}
ALLOWED_URL_HOSTS = {'www.tripper.nl', 'tripper.nl'}


def sanitize_text(text):
    """Strip HTML tags and escape any remaining HTML entities."""
    if not text:
        return ''
    # Remove any HTML tags that survived BeautifulSoup's get_text()
    clean = re.sub(r'<[^>]+>', '', text)
    # Escape HTML entities as a second layer of defense
    return html_escape(clean, quote=True).strip()


def sanitize_url(url):
    """Only allow http(s) URLs pointing to tripper.nl."""
    if not url:
        return ''
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ALLOWED_URL_SCHEMES:
            return ''
        if parsed.hostname not in ALLOWED_URL_HOSTS:
            return ''
        return url
    except Exception:
        return ''


def parse_deals(soup):
    """Parse deal cards from a BeautifulSoup object of the tripper.nl alle-deals page."""
    deals = []
    deal_cards = soup.select('div.deal[data-id]')

    for card in deal_cards:
        deal = {}

        # URL (ensure absolute)
        link = card.select_one('a.deal-link')
        href = link['href'] if link and link.get('href') else ''
        if href and not href.startswith('http'):
            href = 'https://www.tripper.nl' + href
        deal['url'] = sanitize_url(href)

        # Deal name
        h3 = card.select_one('h3')
        deal['name'] = sanitize_text(h3.get_text(strip=True) if h3 else '')

        # Provider
        provider_el = card.select_one('.deal-body .font-normal.text-muted')
        deal['provider'] = sanitize_text(provider_el.get_text(strip=True) if provider_el else '')

        # Location — only take first direct text node, strip everything else
        loc_el = card.select_one('.deal-location')
        if loc_el:
            for child in loc_el.find_all():
                child.decompose()
            raw = loc_el.get_text(strip=True)
            raw = re.sub(r'\(\+.*', '', raw).strip()
            deal['location'] = sanitize_text(raw)
        else:
            deal['location'] = ''

        # Rating
        rating_el = card.select_one('.star-rating small')
        deal['rating'] = sanitize_text(rating_el.get_text(strip=True) if rating_el else '')

        # Discount
        discount_el = card.select_one('.deal-discount')
        discount_text = discount_el.get_text(strip=True) if discount_el else ''
        deal['discount'] = sanitize_text(discount_text)
        m = re.search(r'(\d+)', discount_text)
        deal['discount_num'] = int(m.group(1)) if m else 0

        # Original price (strikethrough)
        orig_el = card.select_one('.text-line-through')
        deal['original_price'] = parse_price(orig_el.get_text(strip=True)) if orig_el else None

        # Discounted price
        price_divs = card.select('.deal-price')
        discounted_price = None
        for div in price_divs:
            if 'from' in div.get('class', []):
                continue
            discounted_price = parse_price(div.get_text(strip=True))
            break
        deal['discounted_price'] = discounted_price

        # Savings
        if deal['original_price'] is not None and deal['discounted_price'] is not None:
            deal['savings'] = round(deal['original_price'] - deal['discounted_price'], 2)
        else:
            deal['savings'] = None

        deals.append(deal)

    return deals


def parse_price(text):
    text = text.replace('\u20ac', '').replace('EUR', '').strip()
    match = re.search(r'(\d+)[,.](\d{2})\b', text)
    if match:
        return float(f"{match.group(1)}.{match.group(2)}")
    match = re.search(r'(\d+)', text)
    if match:
        return float(match.group(1))
    return None


def fetch_live(url="https://www.tripper.nl/alle-deals"):
    import requests
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                       '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'nl-NL,nl;q=0.9,en;q=0.8',
    }
    print(f"Fetching {url} ...")
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    print(f"Received {len(response.content):,} bytes")
    return BeautifulSoup(response.content, 'html.parser')


def load_local(path):
    path = Path(path)
    if not path.exists():
        print(f"Error: file not found: {path}")
        sys.exit(1)
    print(f"Loading {path} ...")
    with open(path, 'r', encoding='utf-8') as f:
        return BeautifulSoup(f.read(), 'html.parser')


# ---------------------------------------------------------------------------
# Geocoding
# ---------------------------------------------------------------------------

def load_geocache():
    if GEOCACHE_FILE.exists():
        with open(GEOCACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_geocache(cache):
    with open(GEOCACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def geocode_locations(deals):
    import requests

    cache = load_geocache()
    unique_locs = set(d['location'] for d in deals if d['location'])
    to_geocode = [loc for loc in unique_locs if loc not in cache]

    if to_geocode:
        print(f"Geocoding {len(to_geocode)} new locations ({len(unique_locs) - len(to_geocode)} cached)...")
        session = requests.Session()
        session.headers.update({'User-Agent': 'TripperDealsScraper/1.0'})

        for i, loc in enumerate(to_geocode):
            query = f"{loc}, Netherlands"
            try:
                r = session.get(
                    'https://nominatim.openstreetmap.org/search',
                    params={'q': query, 'format': 'json', 'limit': 1},
                    timeout=10,
                )
                results = r.json()
                if results:
                    cache[loc] = {'lat': float(results[0]['lat']), 'lng': float(results[0]['lon'])}
                else:
                    r2 = session.get(
                        'https://nominatim.openstreetmap.org/search',
                        params={'q': loc, 'format': 'json', 'limit': 1},
                        timeout=10,
                    )
                    results2 = r2.json()
                    if results2:
                        cache[loc] = {'lat': float(results2[0]['lat']), 'lng': float(results2[0]['lon'])}
                    else:
                        cache[loc] = None
            except Exception as e:
                print(f"  Failed to geocode '{loc}': {e}")
                cache[loc] = None

            if (i + 1) % 10 == 0:
                print(f"  Geocoded {i + 1}/{len(to_geocode)}...")
            time.sleep(1)

        save_geocache(cache)
        print(f"Geocoding complete. Cache now has {len(cache)} entries.")
    else:
        print(f"All {len(unique_locs)} locations already in cache.")

    mapped = 0
    for d in deals:
        coords = cache.get(d['location'])
        if coords:
            d['lat'] = coords['lat']
            d['lng'] = coords['lng']
            mapped += 1
        else:
            d['lat'] = None
            d['lng'] = None

    print(f"Mapped {mapped}/{len(deals)} deals to coordinates.")


# ---------------------------------------------------------------------------
# Data output
# ---------------------------------------------------------------------------

def save_daily_json(deals, date_str):
    """Save deals as data/YYYY-MM-DD.json and update data/index.json manifest."""
    DATA_DIR.mkdir(exist_ok=True)

    # Save deal data
    data_file = DATA_DIR / f"{date_str}.json"
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(deals, f, ensure_ascii=False)
    print(f"Saved {len(deals)} deals to {data_file}")

    # Update manifest
    manifest_file = DATA_DIR / 'index.json'
    if manifest_file.exists():
        with open(manifest_file, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    else:
        manifest = []

    if date_str not in manifest:
        manifest.append(date_str)
    manifest.sort(reverse=True)

    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest updated: {len(manifest)} date(s)")


def main():
    parser = argparse.ArgumentParser(description='Scrape deals from tripper.nl')
    parser.add_argument('--file', '-f', type=str, help='Path to a locally saved HTML file')
    parser.add_argument('--date', '-d', type=str, help='Date label (default: today, YYYY-MM-DD)')
    parser.add_argument('--no-geocode', action='store_true', help='Skip geocoding')
    args = parser.parse_args()

    # Load page
    if args.file:
        soup = load_local(args.file)
        source = args.file
    else:
        soup = fetch_live()
        source = "tripper.nl (live)"

    # Parse
    deals = parse_deals(soup)
    print(f"Extracted {len(deals)} deals from {source}")

    if not deals:
        print("No deals found.")
        return

    # Geocode
    if not args.no_geocode:
        geocode_locations(deals)

    # Save
    date_str = args.date or datetime.now().strftime('%Y-%m-%d')
    save_daily_json(deals, date_str)


if __name__ == "__main__":
    main()
