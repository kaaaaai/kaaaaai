"""Collect completed Douban games without the upstream CSV writer's pubdate assumption."""

import csv
import io
from pathlib import Path

from scripts.backfill_douban import FIELDS, PAGE_SIZE, fetch_page


def render_csv(interests):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FIELDS)
    writer.writeheader()
    seen = set()
    for item in interests:
        subject = item.get('subject') or {}
        identifier = str(subject.get('id') or '')
        title = subject.get('title')
        date = item.get('create_time')
        if not identifier or not title or not date or identifier in seen:
            raise ValueError(f'Incomplete or duplicate game interest: {identifier}')
        seen.add(identifier)
        publication = subject.get('pubdate') or []
        if isinstance(publication, list):
            publication = publication[0] if publication else ''
        rating = subject.get('rating') or {}
        mark_rating = item.get('rating') or {}
        genres = subject.get('genres') or []
        tags = item.get('tags') or []
        writer.writerow({
            'id': identifier,
            'title': title,
            'intro': subject.get('intro') or '',
            'poster': subject.get('cover_url') or
                      f'https://dou.img.lithub.cc/game/{identifier}.jpg',
            'pubdate': publication,
            'url': subject.get('url') or f'https://www.douban.com/game/{identifier}/',
            'rating': rating.get('value') or '',
            'genres': ','.join(genres),
            'star': mark_rating.get('star_count') or '',
            'comment': item.get('comment') or '',
            'tags': ','.join(tags),
            'star_time': date,
            'card': subject.get('card_subtitle') or '',
        })
    return buffer.getvalue()


def main():
    interests = []
    while True:
        page = fetch_page('game', len(interests))
        interests.extend(page)
        if len(page) < PAGE_SIZE:
            break
    text = render_csv(interests)
    if not interests:
        raise ValueError('Douban returned no completed games; existing data preserved')
    path = Path('data/game.csv')
    path.write_text(text, encoding='utf-8')
    print(f'Fetched {len(interests)} completed Douban games')


if __name__ == '__main__':
    main()
