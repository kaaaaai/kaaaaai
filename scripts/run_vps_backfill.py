"""Run one bounded Douban backfill batch on a VPS, never in parallel."""

import fcntl
import json
import os
import secrets
import tempfile
import sys
import time
from pathlib import Path

from scripts.backfill_douban import PAGE_SIZE, DoubanBlocked, backfill, fetch_page
from scripts.check_douban_halt import is_collection_allowed


def run_vps_backfill(root, *, fetch=fetch_page, pause=time.sleep,
                     jitter=secrets.randbelow, is_allowed=is_collection_allowed,
                     lock_path=Path('/var/lock/douban-backfill.lock')):
    root = Path(root)
    with Path(lock_path).open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('Douban backfill already running on VPS') from error
        if (root / 'douban-blocked.flag').exists():
            raise DoubanBlocked('Douban was previously blocked on this VPS; stop now')
        if not is_allowed():
            raise DoubanBlocked('Douban shared refusal signal active; stop now')
        cache = root / 'vps-page-cache'
        cache.mkdir(exist_ok=True)

        def fetch_cached(kind, offset):
            path = cache / f'{kind}-{offset}.json'
            if path.exists():
                try:
                    items = json.loads(path.read_text(encoding='utf-8'))
                except ValueError as error:
                    raise DoubanBlocked(f'Cached {kind} page invalid; stop now') from error
            else:
                items = fetch(kind, offset)
                if not isinstance(items, list) or len(items) > PAGE_SIZE:
                    raise DoubanBlocked(f'{kind} page invalid; stop now')
                fd, temporary = tempfile.mkstemp(prefix='.douban-page-', dir=cache)
                try:
                    with os.fdopen(fd, 'w', encoding='utf-8') as output:
                        json.dump(items, output, ensure_ascii=False)
                    os.replace(temporary, path)
                finally:
                    if os.path.exists(temporary):
                        os.unlink(temporary)
            if not isinstance(items, list) or len(items) > PAGE_SIZE:
                raise DoubanBlocked(f'Cached {kind} page invalid; stop now')
            return items

        return backfill(root, fetch=fetch_cached,
                        pause=lambda seconds: pause(seconds + jitter(21)), max_new=5)


if __name__ == '__main__':
    try:
        print('Added:', run_vps_backfill(Path(__file__).resolve().parents[1]), flush=True)
    except DoubanBlocked as error:
        print(error, file=sys.stderr, flush=True)
        sys.exit(2)
