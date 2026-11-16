"""Regression coverage for the initial and subsequent game CSV exports."""

import csv
import io
import unittest

from scripts.backfill_douban import FIELDS
from scripts.validate_douban_csv import validate_csv
from scripts.fetch_douban_game import render_csv


def game_mark(subject_id, title, date):
    return {
        'subject': {
            'id': subject_id, 'title': title,
            'url': f'https://www.douban.com/game/{subject_id}/',
            'cover_url': 'https://img3.doubanio.com/cover.jpg',
        },
        'create_time': date, 'rating': {'star_count': 4},
        'comment': 'Played', 'tags': ['RPG'],
    }


class GameExportTests(unittest.TestCase):
    def test_game_without_pubdate_exports_poster_and_mark(self):
        text = render_csv([game_mark('36932396', 'Game', '2024-11-04 12:00:00')])
        row = next(csv.DictReader(io.StringIO(text)))
        self.assertEqual(row['id'], '36932396')
        self.assertEqual(row['pubdate'], '')
        self.assertEqual(row['poster'], 'https://img3.doubanio.com/cover.jpg')
        self.assertEqual(row['star_time'], '2024-11-04 12:00:00')
        self.assertEqual(row['star'], '4')

    def test_incomplete_or_duplicate_game_rejected(self):
        with self.assertRaises(ValueError):
            render_csv([game_mark('36932396', '', '2024-11-04')])
        record = game_mark('36932396', 'Game', '2024-11-04')
        with self.assertRaises(ValueError):
            render_csv([record, record])



def game_csv(ids):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FIELDS)
    writer.writeheader()
    for subject in ids:
        writer.writerow({**dict.fromkeys(FIELDS, ''),
                         'id': subject, 'title': 'Game',
                         'poster': 'https://img3.doubanio.com/cover.jpg',
                         'star_time': '2024-11-04'})
    return buffer.getvalue()


class GameCsvValidationTests(unittest.TestCase):
    def test_initial_game_export_must_contain_complete_records(self):
        with self.assertRaises(ValueError):
            validate_csv(None, game_csv([]))
        validate_csv(None, game_csv(['36932396']))

    def test_existing_game_subjects_cannot_disappear(self):
        with self.assertRaises(ValueError):
            validate_csv(game_csv(['36932396', '36961754']), game_csv(['36932396']))


if __name__ == '__main__':
    unittest.main()
