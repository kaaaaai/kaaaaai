import csv
import tempfile
import unittest
from pathlib import Path

from scripts.backfill_douban import backfill, DoubanBlocked


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


if __name__ == '__main__':
    unittest.main()
