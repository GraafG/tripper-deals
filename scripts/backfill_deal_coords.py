"""One-shot backfill: fetch precise coordinates for every deal URL that has
ever appeared in data/*.json and rewrite each daily snapshot with the new
lat/lng/address.

After this runs once, ongoing scrapes will only need to fetch the detail
page for *new* deal URLs (handled automatically in tripper_scraper.py).

Usage (run from repo root):
    python scripts/backfill_deal_coords.py            # only fetch URLs not yet cached
    python scripts/backfill_deal_coords.py --force    # re-fetch every URL
"""
import argparse
import json
import sys
from pathlib import Path

# Allow importing from repo root when run as scripts/backfill_deal_coords.py
sys.path.insert(0, str(Path(__file__).parent.parent))

from tripper_scraper import (
    DATA_DIR,
    enrich_deals_with_detail_coords,
    load_dealcache,
)


def collect_all_deals():
    """Return a deduplicated list of {url} stubs from every daily snapshot."""
    seen = {}
    for path in sorted(DATA_DIR.glob('*.json')):
        if path.name == 'index.json':
            continue
        if path.name == 'history.json':
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                deals = json.load(f)
        except Exception as e:
            print(f"  Skipping {path.name}: {e}")
            continue
        if not isinstance(deals, list):
            continue
        for d in deals:
            url = d.get('url')
            if url and url not in seen:
                seen[url] = {'url': url}
    return list(seen.values())


def apply_cache_to_snapshots():
    """Rewrite every data/YYYY-MM-DD.json with lat/lng/address from the cache."""
    cache = load_dealcache()
    updated_files = 0
    for path in sorted(DATA_DIR.glob('*.json')):
        if path.name in ('index.json', 'history.json'):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                deals = json.load(f)
        except Exception as e:
            print(f"  Skipping {path.name}: {e}")
            continue
        if not isinstance(deals, list):
            continue

        changed = False
        for d in deals:
            coords = cache.get(d.get('url'))
            if not coords:
                continue
            new_lat = coords['lat']
            new_lng = coords['lng']
            new_addr = coords.get('address') or d.get('address')
            new_locs = coords.get('locations')
            if not new_locs:
                new_locs = [{'lat': new_lat, 'lng': new_lng,
                             'address': coords.get('address', '')}]
            if (d.get('lat') != new_lat or d.get('lng') != new_lng
                    or d.get('address') != new_addr
                    or d.get('locations') != new_locs):
                d['lat'] = new_lat
                d['lng'] = new_lng
                if new_addr:
                    d['address'] = new_addr
                d['locations'] = new_locs
                changed = True

        if changed:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(deals, f, ensure_ascii=False, indent=2)
            updated_files += 1
            print(f"  Updated {path.name}")

    print(f"Rewrote {updated_files} snapshot file(s).")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--force', action='store_true',
                        help='Re-fetch every deal even if already cached.')
    args = parser.parse_args()

    deals = collect_all_deals()
    print(f"Found {len(deals)} unique deal URL(s) across all snapshots.")

    enrich_deals_with_detail_coords(deals, force=args.force)
    apply_cache_to_snapshots()


if __name__ == '__main__':
    main()
