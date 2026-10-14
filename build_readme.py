import asyncio
import httpx
import feedparser
import pathlib
import re
import sys
import datetime
from typing import List, Dict, Any

root = pathlib.Path(__file__).parent.resolve()

def replace_chunk(content: str, marker: str, chunk: str, inline: bool = False) -> str:
    r = re.compile(
        r"<!\-\- {} starts \-\->.*<!\-\- {} ends \-\->".format(marker, marker),
        re.DOTALL,
    )
    if not inline:
        chunk = "\n{}\n".format(chunk)
    chunk = "<!-- {} starts -->{}<!-- {} ends -->".format(marker, chunk, marker)
    return r.sub(chunk, content)

def format_gmt_time(timestamp: str) -> datetime.date:
    GMT_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'
    date_str = datetime.datetime.strptime(timestamp, GMT_FORMAT) + datetime.timedelta(hours=8)
    return date_str.date()

async def fetch_douban() -> List[Dict[str, Any]]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    async with httpx.AsyncClient(headers=headers, timeout=30.0, follow_redirects=True) as client:
        try:
            response = await client.get("https://www.douban.com/feed/people/kaaaaai/interests")
            response.raise_for_status()
            feed = feedparser.parse(response.text)
            return [
                {
                    "title": item["title"],
                    "url": item["link"].split("#")[0],
                    "published": format_gmt_time(item["published"])
                }
                for item in feed["entries"]
            ]
        except httpx.HTTPStatusError as e:
            print(f"Error fetching Douban data: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error fetching Douban data: {e}")
            return []

async def fetch_blog_entries() -> List[Dict[str, Any]]:
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            response = await client.get("https://kaaaaai.cn/atom.xml")
            response.raise_for_status()
            feed = feedparser.parse(response.text)
            return [
                {
                    "title": entry["title"],
                    "url": entry["link"].split("#")[0],
                    "published": entry["published"].split("T")[0],
                }
                for entry in feed["entries"]
            ]
        except httpx.HTTPStatusError as e:
            print(f"Error fetching blog entries: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error fetching blog entries: {e}")
            return []

async def fetch_memos():
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get("https://memos.kaaaaai.cn/api/v1/memos?openId=bff14007-bcff-4dc2-80ff-5ab9fd61170f")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error fetching memos: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error fetching memos: {e}")
            return []

async def main():
    if len(sys.argv) < 2:
        print("Please provide the input file name as an argument.")
        sys.exit(1)

    input_file = sys.argv[1]
    readme = root / input_file

    readme_contents = readme.read_text()
    rewritten = readme_contents

    doubans = await fetch_douban()
    if doubans:
        doubans_md = "\n".join(
            ["- [{title}]({url}) {published}".format(**item) for item in doubans[:10]]
        )
        rewritten = replace_chunk(rewritten, "douban", doubans_md)
    else:
        print("Skipping Douban update due to error.")

    entries = await fetch_blog_entries()
    if entries:
        entries_md = "\n".join(
            ["- [{title}]({url})".format(**entry) for entry in entries[:10]]
        )
        rewritten = replace_chunk(rewritten, "blog", entries_md)
    else:
        print("Skipping blog entries update due to error.")

    readme.write_text(rewritten)

    # Uncomment the following line if you want to use fetch_memos
    # memos = await fetch_memos()
    # print(memos)

if __name__ == "__main__":
    asyncio.run(main())
