"""Run one bounded Douban backfill batch on a VPS, never in parallel."""

import fcntl
import secrets
import sys
import time
from pathlib import Path

from scripts.backfill_douban import DoubanBlocked, backfill, fetch_page
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
        return backfill(root, fetch=fetch,
                        pause=lambda seconds: pause(seconds + jitter(21)), max_new=3)


if __name__ == '__main__':
    try:
        print('Added:', run_vps_backfill(Path(__file__).resolve().parents[1]), flush=True)
    except DoubanBlocked as error:
        print(error, file=sys.stderr, flush=True)
        sys.exit(2)
