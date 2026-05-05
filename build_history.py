"""Build a unified price-history file from daily deal snapshots.

Reads every data/YYYY-MM-DD.json produced by the scraper and writes
data/history.json keyed by deal URL.  Each entry contains the full
price timeline plus pre-computed summary fields so the frontend can
render trend arrows, "lowest-price" badges, and sparkline charts
without extra computation.
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'


def build_history():
    manifest_file = DATA_DIR / 'index.json'
    if not manifest_file.exists():
        print("No data/index.json found — nothing to do.")
        return

    with open(manifest_file, 'r', encoding='utf-8') as f:
        dates = json.load(f)

    # Sort chronologically (oldest first) for proper timeline building
    dates_asc = sorted(dates)

    history = {}  # keyed by deal URL

    for date_str in dates_asc:
        data_file = DATA_DIR / f"{date_str}.json"
        if not data_file.exists():
            continue

        with open(data_file, 'r', encoding='utf-8') as f:
            deals = json.load(f)

        for deal in deals:
            url = deal.get('url')
            if not url:
                continue

            price = deal.get('discounted_price')

            if url not in history:
                history[url] = {
                    'name': deal.get('name', ''),
                    'location': deal.get('location', ''),
                    'provider': deal.get('provider', ''),
                    'prices': [],
                    'first_seen': date_str,
                    'last_seen': date_str,
                }

            entry = history[url]
            entry['last_seen'] = date_str
            # Keep name/provider/location up-to-date with latest snapshot
            entry['name'] = deal.get('name', '') or entry['name']
            entry['location'] = deal.get('location', '') or entry['location']
            entry['provider'] = deal.get('provider', '') or entry['provider']

            entry['prices'].append({
                'date': date_str,
                'price': price,
                'original': deal.get('original_price'),
                'discount_num': deal.get('discount_num', 0),
            })

    # Compute summary fields
    latest_date = dates_asc[-1] if dates_asc else None
    for url, entry in history.items():
        valid_prices = [p['price'] for p in entry['prices'] if p['price'] is not None]

        if valid_prices:
            entry['min_price'] = min(valid_prices)
            entry['max_price'] = max(valid_prices)
            entry['current_price'] = valid_prices[-1]
            entry['at_lowest'] = valid_prices[-1] <= entry['min_price']
        else:
            entry['min_price'] = None
            entry['max_price'] = None
            entry['current_price'] = None
            entry['at_lowest'] = False

        # Trend: compare last two *distinct* price values (ignore unchanged runs)
        distinct = []
        for p in reversed(valid_prices):
            if not distinct or p != distinct[-1]:
                distinct.append(p)
            if len(distinct) == 2:
                break
        if len(distinct) == 2:
            prev, curr = distinct[1], distinct[0]
            if curr < prev:
                entry['trend'] = 'down'
            elif curr > prev:
                entry['trend'] = 'up'
            else:
                entry['trend'] = 'stable'
        else:
            entry['trend'] = 'new'

        entry['days_tracked'] = len(entry['prices'])
        entry['is_active'] = (entry['last_seen'] == latest_date)

    # Write output
    out_file = DATA_DIR / 'history.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False)

    print(f"Built history for {len(history)} deals across {len(dates_asc)} dates → {out_file}")
    at_lowest = sum(1 for e in history.values() if e.get('at_lowest'))
    print(f"  {at_lowest} deals currently at their lowest tracked price")


if __name__ == '__main__':
    build_history()
