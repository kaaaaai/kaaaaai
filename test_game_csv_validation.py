"""Regression coverage for the initial and subsequent game CSV exports."""

import csv
import io
import unittest

from scripts.backfill_douban import FIELDS
from scripts.validate_douban_csv import validate_csv


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
