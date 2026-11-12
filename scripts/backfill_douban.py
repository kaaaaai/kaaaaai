"""Backfill at most one older completed Douban mark per category per run."""

import csv
import json
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FIELDS = ('id', 'title', 'intro', 'poster', 'pubdate', 'url', 'rating', 'genres',
          'star', 'comment', 'tags', 'star_time', 'card')
KINDS = ('movie', 'music', 'book')
PAGE_SIZE = 50
# Same public client key and endpoint used by the existing doumark-action.
DOUBAN_API_KEY = '0ac44ae016490db2204ce0a042db2916'


class DoubanBlocked(RuntimeError):
    """Stop immediately rather than retrying or changing endpoints."""


def fetch_page(kind, offset):
    url = 'https://frodo.douban.com/api/v2/user/kaaaaai/interests?' + urlencode({
        'type': kind, 'status': 'done', 'count': PAGE_SIZE,
        'start': offset, 'apiKey': DOUBAN_API_KEY,
    })
    request = Request(url, headers={
        'User-Agent': 'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 15_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.16(0x18001023) NetType/WIFI Language/zh_CN',
        'Referer': 'https://servicewechat.com/wx2f9b06c1de1ccfca/84/page-frame.html',
    })
    try:
        with urlopen(request, timeout=15) as response:
            if response.status != 200:
                raise DoubanBlocked(f'Douban refused HTTP {response.status}; stop now')
            payload = json.load(response)
    except HTTPError as error:
        raise DoubanBlocked(f'Douban refused HTTP {error.code}; stop now') from error
    except (URLError, TimeoutError, ValueError) as error:
        raise DoubanBlocked(f'Douban response unavailable or invalid; stop now: {error}') from error
    if not isinstance(payload, dict) or not isinstance(payload.get('interests'), list):
        raise DoubanBlocked('Douban response changed or requires verification; stop now')
    return payload['interests']


def format_mark(mark, kind):
    subject = mark.get('subject') or {}
    identifier = str(subject.get('id') or '')
    timestamp = mark.get('create_time')
    if not identifier.isdecimal() or not subject.get('title') or not isinstance(timestamp, str):
        raise DoubanBlocked('Douban record changed shape; stop now')
    try:
        datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
    except ValueError as error:
        raise DoubanBlocked('Douban record date changed shape; stop now') from error
    pubdate = subject.get('pubdate') or []
    rating = subject.get('rating') or {}
    personal_rating = mark.get('rating') or {}
    return dict(zip(FIELDS, (
        identifier, subject['title'], subject.get('intro') or '',
        f'https://dou.img.lithub.cc/{kind}/{identifier}.jpg',
        pubdate[0] if isinstance(pubdate, list) and pubdate else '',
        subject.get('url') or '', rating.get('value') or '',
        ','.join(subject.get('genres') or []), personal_rating.get('star_count') or '',
        mark.get('comment') or '', ','.join(mark.get('tags') or []), timestamp,
        subject.get('card_subtitle') or '',
    )))


def backfill(root, fetch=fetch_page, pause=time.sleep):
    data = Path(root) / 'data'
    prepared = {}
    added = {}
    for index, kind in enumerate(KINDS):
        path = data / f'{kind}.csv'
        with path.open(newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            if tuple(reader.fieldnames or ()) != FIELDS:
                raise ValueError(f'{kind} CSV schema mismatch')
            rows = list(reader)
        ids = {row['id'] for row in rows}
        if len(ids) != len(rows) or not rows:
            raise ValueError(f'{kind} CSV missing or has duplicate IDs')
        if index:
            pause(20)
        offset = (len(rows) // PAGE_SIZE) * PAGE_SIZE
        interests = fetch(kind, offset)
        if not isinstance(interests, list) or len(interests) > PAGE_SIZE:
            raise DoubanBlocked(f'{kind} response invalid; stop now')
        oldest = min(row['star_time'] for row in rows)
        new = []
        for mark in interests:
            item = format_mark(mark, kind)
            if item['id'] not in ids and item['star_time'] < oldest:
                new.append(item)
        new.sort(key=lambda item: item['star_time'], reverse=True)
        added[kind] = min(len(new), 1)
        if new:
            prepared[path] = sorted(rows + new[:1],
                                    key=lambda item: item['star_time'], reverse=True)
        print(f'{kind}: offset={offset}, response={len(interests)}, older={len(new)}, add={added[kind]}', flush=True)

    # Network responses for all categories are validated before changing any CSV.
    for path, rows in prepared.items():
        fd, temporary = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
        try:
            with os.fdopen(fd, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return added


if __name__ == '__main__':
    try:
        print('Added:', backfill(Path(__file__).resolve().parents[1]), flush=True)
    except DoubanBlocked as error:
        print(error, file=sys.stderr, flush=True)
        sys.exit(2)
