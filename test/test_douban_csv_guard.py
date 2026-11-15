import csv
import io
import unittest

from scripts.validate_douban_csv import validate_csv


FIELDS = ('id', 'title', 'intro', 'poster', 'pubdate', 'url', 'rating',
          'genres', 'star', 'comment', 'tags', 'star_time', 'card')


def csv_data(*identifiers):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FIELDS)
    writer.writeheader()
    for identifier in identifiers:
        writer.writerow({'id': identifier, 'title': f'Title {identifier}',
                         'poster': f'https://example.com/{identifier}.jpg',
                         'star_time': '2026-11-15 12:00:00'})
    return buffer.getvalue()


class DoubanCsvGuardTests(unittest.TestCase):
    def test_accepts_new_records_without_losing_existing_ids(self):
        validate_csv(csv_data('1', '2'), csv_data('2', '3', '1'))

    def test_rejects_truncated_collection_before_commit(self):
        with self.assertRaisesRegex(ValueError, 'missing'):
            validate_csv(csv_data('1', '2'), csv_data('2'))

    def test_rejects_duplicate_subjects(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            validate_csv(csv_data('1'), csv_data('1', '1'))

    def test_rejects_empty_or_schema_changed_collection(self):
        with self.assertRaises(ValueError):
            validate_csv(csv_data('1'), 'id,title\n')


if __name__ == '__main__':
    unittest.main()
