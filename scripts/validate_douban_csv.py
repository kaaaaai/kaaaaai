"""Reject truncated or malformed Douban CSV refreshes before committing them."""

import csv
import io
import subprocess
from pathlib import Path

from scripts.backfill_douban import FIELDS


KINDS = ('book', 'movie', 'music', 'game')


def validate_csv(previous_text, current_text):
    def ids(text):
        reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError('Douban CSV schema changed')
        rows = list(reader)
        subjects = [row['id'] for row in rows]
        if not subjects or any(not row['id'] or not row['title'] or
                               not row['poster'] or not row['star_time'] for row in rows):
            raise ValueError('Douban CSV has empty or incomplete records')
        if len(subjects) != len(set(subjects)):
            raise ValueError('Douban CSV has duplicate subject IDs')
        return set(subjects)

    current_ids = ids(current_text)
    missing = ids(previous_text) - current_ids if previous_text is not None else set()
    if missing:
        raise ValueError(f'Douban CSV missing {len(missing)} existing subject IDs')


def main():
    for kind in KINDS:
        path = Path('data') / f'{kind}.csv'
        result = subprocess.run(['git', 'show', f'HEAD:{path}'],
                                capture_output=True, text=True)
        if result.returncode and kind != 'game':
            result.check_returncode()
        validate_csv(result.stdout if result.returncode == 0 else None,
                     path.read_text(encoding='utf-8-sig'))
        print(f'{kind}: retained all existing subject IDs')


if __name__ == '__main__':
    main()
