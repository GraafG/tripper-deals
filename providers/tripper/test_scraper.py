"""Offline pagination fixtures: python -m unittest discover -s providers/tripper."""
import unittest
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup

import scraper


BASE = 'https://www.tripper.nl/alle-deals'


def card(deal_id, slug=None):
    slug = slug or deal_id
    return f'''
    <div class="deal" data-id="{deal_id}">
      <a class="deal-link" href="/deals/{slug}"><h3>Deal {deal_id}</h3></a>
      <div class="deal-body"><span class="font-normal text-muted">Venue</span></div>
      <div class="deal-location">Amsterdam <span>(+2 locaties)</span></div>
      <span class="deal-discount">50%</span>
      <span class="text-line-through">EUR 20,00</span>
      <div class="deal-price from">Vanaf</div><div class="deal-price">EUR 10,00</div>
    </div>'''


def fixture_fetch(pages):
    return Mock(side_effect=lambda url: BeautifulSoup(pages[url], 'html.parser'))


class PaginationTests(unittest.TestCase):
    def test_full_pages_collect_more_than_48_and_deduplicate(self):
        fetch = fixture_fetch({
            BASE: ''.join(card(str(i)) for i in range(48))
            + '<link rel="next" href="/alle-deals?page=2">',
            BASE + '?page=2': card('47') + ''.join(card(str(i)) for i in range(48, 96))
            + '<a rel="next" href="?page=3">Next</a>',
            BASE + '?page=3': card('96'),
        })
        deals = scraper.fetch_all_deals(fetch_page=fetch)
        self.assertEqual(len(deals), 97)
        self.assertEqual(fetch.call_count, 3)
        self.assertEqual(deals[0]['url'], 'https://www.tripper.nl/deals/0')
        self.assertEqual(deals[0]['location'], 'Amsterdam')
        self.assertEqual(deals[0]['discounted_price'], 10.0)
        self.assertEqual(deals[0]['savings'], 10.0)
        self.assertNotIn('id', deals[0])

    def test_current_fragment_markers_and_final_batch(self):
        fetch = fixture_fetch({
            BASE: card('1') + '''
              <a href="/alle-deals?page=2" rel="next" data-all-deals-more
                 data-fragment-url="/alle-deals/batch?page=2">More</a>''',
            BASE + '/batch?page=2': card('1') + card('2') + '''
              <div hidden data-all-deals-next data-href="/alle-deals?page=3"
                   data-fragment-url="/alle-deals/batch?page=3"></div>''',
            BASE + '/batch?page=3': card('3') + '''
              <div hidden data-all-deals-next data-href=""
                   data-fragment-url="" data-loaded-message="1 extra deals geladen"></div>''',
        })
        deals = scraper.fetch_all_deals(fetch_page=fetch)
        self.assertEqual([d['name'] for d in deals], ['Deal 1', 'Deal 2', 'Deal 3'])
        self.assertEqual(fetch.call_count, 3)

    def test_fragment_marker_falls_back_to_full_page(self):
        fetch = fixture_fetch({
            BASE: card('1') + '<div data-all-deals-next data-href="/alle-deals?page=2"></div>',
            BASE + '?page=2': card('2'),
        })
        self.assertEqual(len(scraper.fetch_all_deals(fetch_page=fetch)), 2)

    def test_numbered_links_ignore_previous_pages_and_other_paths(self):
        fetch = fixture_fetch({
            BASE: card('1') + '<a href="?page=3">3</a><a href="?page=2">2</a>',
            BASE + '?page=2': card('2') + '<a href="?page=1">1</a><a href="?page=3">3</a>',
            BASE + '?page=3': card('3') + '<a href="?page=2">2</a><a href="/other?page=4">4</a>',
        })
        self.assertEqual(len(scraper.fetch_all_deals(fetch_page=fetch)), 3)

    def test_deduplicates_by_id_and_url(self):
        fetch = fixture_fetch({
            BASE: card('1') + card('1', 'alias') + card('different-id', '1') + card('2'),
        })
        self.assertEqual(len(scraper.fetch_all_deals(fetch_page=fetch)), 2)

    def test_single_page_still_works(self):
        fetch = fixture_fetch({BASE: card('1')})
        self.assertEqual(len(scraper.fetch_all_deals(fetch_page=fetch)), 1)
        fetch.assert_called_once_with(BASE)

    def test_repeated_cards_fail_instead_of_returning_partial_data(self):
        fetch = fixture_fetch({
            BASE: card('1') + '<a rel="next" href="?page=2">2</a>',
            BASE + '?page=2': card('1'),
        })
        with self.assertRaisesRegex(ValueError, 'only repeated deals'):
            scraper.fetch_all_deals(fetch_page=fetch)

    def test_bad_next_links_fail(self):
        for href in ['?page=1', '?page=0', '?page=3', '?page=abc',
                     'https://example.org/alle-deals?page=2']:
            with self.subTest(href=href):
                fetch = fixture_fetch({BASE: card('1') + f'<link rel="next" href="{href}">'})
                with self.assertRaises(ValueError):
                    scraper.fetch_all_deals(fetch_page=fetch)

    def test_missing_marker_url_fails(self):
        fetch = fixture_fetch({BASE: card('1') + '<div data-all-deals-next></div>'})
        with self.assertRaisesRegex(ValueError, 'Missing next listing URL'):
            scraper.fetch_all_deals(fetch_page=fetch)

    def test_http_errors_propagate(self):
        scraper_error = RuntimeError('HTTP failure')
        fetch = Mock(side_effect=[
            BeautifulSoup(card('1') + '<link rel="next" href="?page=2">', 'html.parser'),
            scraper_error,
        ])
        with self.assertRaises(RuntimeError) as caught:
            scraper.fetch_all_deals(fetch_page=fetch)
        self.assertIs(caught.exception, scraper_error)

    def test_empty_advertised_page_is_not_a_successful_partial_scrape(self):
        for path in ['', '/batch']:
            with self.subTest(path=path):
                fetch = fixture_fetch({
                    BASE: card('1') + f'<link rel="next" href="/alle-deals{path}?page=2">',
                    BASE + path + '?page=2': '<html>Unexpected response</html>',
                })
                with self.assertRaisesRegex(ValueError, 'No deal cards'):
                    scraper.fetch_all_deals(fetch_page=fetch)

    def test_batch_without_successor_fails_before_save(self):
        pages = {
            BASE: card('1') + '''
              <a href="/alle-deals?page=2" data-all-deals-more
                 data-fragment-url="/alle-deals/batch?page=2">More</a>''',
            BASE + '/batch?page=2': card('2'),
        }
        with patch('sys.argv', ['scraper.py', '--no-geocode']), \
                patch.object(scraper, 'fetch_live', side_effect=lambda url: BeautifulSoup(
                    pages[url], 'html.parser')), \
                patch.object(scraper, 'save_daily_json') as save:
            with self.assertRaisesRegex(ValueError, 'no successor or final marker'):
                scraper.main()
            save.assert_not_called()

    def test_local_file_mode_does_not_fetch_listing(self):
        with patch('sys.argv', ['scraper.py', '--file', 'fixture.html', '--no-geocode']), \
                patch.object(scraper, 'load_local', return_value=BeautifulSoup(card('1'), 'html.parser')), \
                patch.object(scraper, 'fetch_all_deals') as fetch, \
                patch.object(scraper, 'save_daily_json') as save:
            scraper.main()
            fetch.assert_not_called()
            self.assertEqual(len(save.call_args.args[0]), 1)


if __name__ == '__main__':
    unittest.main()
