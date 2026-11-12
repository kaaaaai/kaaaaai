"""Stop all Douban collection when the cover publisher reports a refusal."""

import sys
from urllib.error import HTTPError
from urllib.request import urlopen

SIGNAL_URL = ('https://raw.githubusercontent.com/kaaaaai/'
              'kaaaaai.tools.token-usage-public/main/douban/blocked.flag')


def is_collection_allowed(fetch=urlopen):
    try:
        with fetch(SIGNAL_URL, timeout=15) as response:
            return response.status == 404
    except HTTPError as error:
        if error.code == 404:
            return True
        raise


if __name__ == '__main__':
    if not is_collection_allowed():
        print('Douban cover publisher reported access refusal; collection stopped.',
              file=sys.stderr)
        sys.exit(1)
