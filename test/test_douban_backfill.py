import csv
import tempfile
import unittest
from urllib.error import HTTPError
from unittest.mock import Mock
from pathlib import Path

from scripts.backfill_douban import backfill, DoubanBlocked
from scripts.check_douban_halt import is_collection_allowed


HEADERS = ('id', 'title', 'intro', 'poster', 'pubdate', 'url', 'rating', 'genres',
           'star', 'comment', 'tags', 'star_time', 'card')


def interest(id, timestamp):
    return {
        'create_time': timestamp,
        'subject': {
            'id': str(id), 'title': f'Title {id}', 'intro': '',
            'pubdate': ['2020'], 'url': f'https://movie.douban.com/subject/{id}/',
            'rating': {'value': 8.0}, 'genres': ['Drama'], 'card_subtitle': '2020',
        },
        'rating': {'star_count': 4}, 'comment': 'Review', 'tags': ['Favorite'],
    }


class BackfillTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = self.root / 'data'
        self.data.mkdir()
        for kind in ('movie', 'music', 'book'):
            with (self.data / f'{kind}.csv').open('w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=HEADERS)
                writer.writeheader()
                writer.writerow({'id': '1', 'title': 'Existing',
                                 'star_time': '2023-05-06 14:12:37'})

    def rows(self, kind):
        with (self.data / f'{kind}.csv').open(newline='') as file:
            return list(csv.DictReader(file))

    def test_adds_at_most_one_older_record_per_kind_without_duplicates(self):
        calls = []
        def fetch(kind, offset):
            calls.append((kind, offset))
            return [interest(1, '2023-05-06 14:12:37'),
                    interest(2, '2022-04-01 10:00:00'),
                    interest(3, '2021-04-01 10:00:00')]

        result = backfill(self.root, fetch, pause=lambda seconds: None)

        self.assertEqual(result, {'movie': 1, 'music': 1, 'book': 1})
        self.assertEqual(calls, [('movie', 0), ('music', 0), ('book', 0)])
        self.assertEqual([row['id'] for row in self.rows('movie')], ['1', '2'])
        self.assertEqual(self.rows('book')[1]['poster'],
                         'https://dou.img.lithub.cc/book/2.jpg')

    def test_backfills_missing_mark_even_when_newer_than_oldest_csv_entry(self):
        def fetch(kind, offset):
            return [interest(2, '2024-01-01 10:00:00'),
                    interest(1, '2023-05-06 14:12:37')]

        result = backfill(self.root, fetch, pause=lambda seconds: None)

        self.assertEqual(result['movie'], 1)
        self.assertEqual([row['id'] for row in self.rows('movie')], ['2', '1'])

    def test_advances_cursor_after_full_page_already_in_csv(self):
        for kind in ('movie', 'music', 'book'):
            with (self.data / f'{kind}.csv').open('a', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=HEADERS)
                for id in range(2, 51):
                    writer.writerow({'id': str(id), 'title': f'Existing {id}',
                                     'star_time': '2023-05-06 14:12:37'})
        calls = []
        def fetch(kind, offset):
            calls.append((kind, offset))
            if offset == 50:
                return [interest(id, '2023-05-06 14:12:37') for id in range(1, 51)]
            return [interest(51, '2022-04-01 10:00:00')]

        self.assertEqual(backfill(self.root, fetch, pause=lambda seconds: None),
                         {'movie': 0, 'music': 0, 'book': 0})
        self.assertEqual(backfill(self.root, fetch, pause=lambda seconds: None),
                         {'movie': 1, 'music': 1, 'book': 1})
        self.assertEqual(calls, [('movie', 50), ('music', 50), ('book', 50),
                                 ('movie', 100), ('music', 100), ('book', 100)])

    def test_bounded_batch_resumes_remaining_marks_on_next_run(self):
        def fetch(kind, offset):
            return [interest(1, '2023-05-06 14:12:37')] + [
                interest(id, f'2022-04-{id:02d} 10:00:00')
                for id in range(2, 7)
            ]

        first = backfill(self.root, fetch, pause=lambda seconds: None, max_new=3)
        second = backfill(self.root, fetch, pause=lambda seconds: None, max_new=3)

        self.assertEqual(first, {'movie': 3, 'music': 3, 'book': 3})
        self.assertEqual(second, {'movie': 2, 'music': 2, 'book': 2})
        self.assertEqual({row['id'] for row in self.rows('movie')},
                         {str(id) for id in range(1, 7)})

    def test_refusal_does_not_write_any_partial_csv(self):
        before = {kind: (self.data / f'{kind}.csv').read_bytes()
                  for kind in ('movie', 'music', 'book')}
        def fetch(kind, offset):
            if kind == 'music':
                raise DoubanBlocked('HTTP 418')
            return [interest(1, '2023-05-06 14:12:37'),
                    interest(2, '2022-04-01 10:00:00')]

        with self.assertRaisesRegex(DoubanBlocked, '418'):
            backfill(self.root, fetch, pause=lambda seconds: None)

        self.assertEqual(before, {kind: (self.data / f'{kind}.csv').read_bytes()
                                  for kind in before})
        self.assertTrue((self.root / 'douban-blocked.flag').exists())

    def test_shared_stop_signal_blocks_further_collection(self):
        blocked = Mock()
        blocked.__enter__ = Mock(return_value=Mock(status=200))
        blocked.__exit__ = Mock(return_value=False)
        self.assertFalse(is_collection_allowed(fetch=lambda url, timeout: blocked))

    def test_absent_signal_allows_collection_but_other_errors_fail_closed(self):
        def unavailable(code):
            def fetch(url, timeout):
                error = HTTPError(url, code, 'HTTP error', {}, None)
                self.addCleanup(error.close)
                raise error
            return fetch
        self.assertTrue(is_collection_allowed(fetch=unavailable(404)))
        with self.assertRaises(HTTPError):
            is_collection_allowed(fetch=unavailable(503))


if __name__ == '__main__':
    unittest.main()
