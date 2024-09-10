import asyncio
from python_graphql_client import GraphqlClient
import feedparser
import httpx
import json
import pathlib
import re
import os
import sys
import datetime
from typing import List, Dict, Any

root = pathlib.Path(__file__).parent.resolve()
client = GraphqlClient(endpoint="https://api.github.com/graphql")

GITHUB_TOKEN = os.environ.get("PERSONAL_TOKEN", "")

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

def make_query(after_cursor: str = None) -> str:
    return """
query {
  viewer {
    repositories(first: 100, privacy: PUBLIC, after:AFTER) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        name
        description
        url
        releases(first:1) {
          totalCount
          nodes {
            name
            publishedAt
            url
          }
        }
      }
    }
  }
}
""".replace(
        "AFTER", '"{}"'.format(after_cursor) if after_cursor else "null"
    )

async def fetch_releases(oauth_token: str) -> List[Dict[str, Any]]:
    releases = []
    repo_names = set()
    has_next_page = True
    after_cursor = None

    async with httpx.AsyncClient() as client:
        while has_next_page:
            response = await client.post(
                "https://api.github.com/graphql",
                json={"query": make_query(after_cursor)},
                headers={"Authorization": f"Bearer {oauth_token}"}
            )
            data = response.json()

            for repo in data["data"]["viewer"]["repositories"]["nodes"]:
                if repo["releases"]["totalCount"] and repo["name"] not in repo_names:
                    releases_nodes = repo["releases"]["nodes"]
                    filtered_nodes = [node for node in releases_nodes if node["publishedAt"]]
                    if filtered_nodes:
                        latest_release = filtered_nodes[-1]
                        repo_names.add(repo["name"])
                        releases.append({
                            "repo": repo["name"],
                            "repo_url": repo["url"],
                            "description": repo["description"],
                            "release": latest_release["name"].replace(repo["name"], "").strip(),
                            "published_at": latest_release["publishedAt"].split("T")[0],
                            "url": latest_release["url"],
                        })

            has_next_page = data["data"]["viewer"]["repositories"]["pageInfo"]["hasNextPage"]
            after_cursor = data["data"]["viewer"]["repositories"]["pageInfo"]["endCursor"]

    return releases

def fetch_douban() -> List[Dict[str, Any]]:
    entries = feedparser.parse("https://www.douban.com/feed/people/kaaaaai/interests")["entries"]
    return [
        {
            "title": item["title"],
            "url": item["link"].split("#")[0],
            "published": format_gmt_time(item["published"])
        }
        for item in entries
    ]

def fetch_blog_entries() -> List[Dict[str, Any]]:
    entries = feedparser.parse("https://kaaaaai.cn/atom.xml")["entries"]
    return [
        {
            "title": entry["title"],
            "url": entry["link"].split("#")[0],
            "published": entry["published"].split("T")[0],
        }
        for entry in entries
    ]

async def fetch_memos():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://memos.kaaaaai.cn/api/v1/memos?openId=bff14007-bcff-4dc2-80ff-5ab9fd61170f")
        return response.json()

async def main():
    if len(sys.argv) < 2:
        print("Please provide the input file name as an argument.")
        sys.exit(1)

    input_file = sys.argv[1]
    readme = root / input_file
    project_releases = root / "releases.md"

    releases = await fetch_releases(GITHUB_TOKEN)
    releases.sort(key=lambda r: r["published_at"], reverse=True)
    md = "\n".join(
        [
            "- [{repo}]({url})：{release}".format(**release)
            for release in releases[:10]
        ]
    )
    readme_contents = readme.read_text()
    rewritten = replace_chunk(readme_contents, "recent_releases", md)

    doubans = fetch_douban()[:10]
    doubans_md = "\n".join(
        ["- [{title}]({url}) {published}".format(**item) for item in doubans]
    )
    rewritten = replace_chunk(rewritten, "douban", doubans_md)

    entries = fetch_blog_entries()[:10]
    entries_md = "\n".join(
        ["- [{title}]({url})".format(**entry) for entry in entries]
    )
    rewritten = replace_chunk(rewritten, "blog", entries_md)

    readme.write_text(rewritten)

    # Uncomment the following line if you want to use fetch_memos
    # memos = await fetch_memos()
    # print(memos)

if __name__ == "__main__":
    asyncio.run(main())