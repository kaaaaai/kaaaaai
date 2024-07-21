from python_graphql_client import GraphqlClient
import feedparser
import httpx
import json
import pathlib
import re
import os
import sys
import datetime

root = pathlib.Path(__file__).parent.resolve()
client = GraphqlClient(endpoint="https://api.github.com/graphql")

GITHUB_TOKEN = os.environ.get("PERSONAL_TOKEN", "")


def replace_chunk(content, marker, chunk, inline=False):
    r = re.compile(
        r"<!\-\- {} starts \-\->.*<!\-\- {} ends \-\->".format(marker, marker),
        re.DOTALL,
    )
    if not inline:
        chunk = "\n{}\n".format(chunk)
    chunk = "<!-- {} starts -->{}<!-- {} ends -->".format(
        marker, chunk, marker)
    return r.sub(chunk, content)


def formatGMTime(timestamp):
    GMT_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'
    dateStr = datetime.datetime.strptime(
        timestamp, GMT_FORMAT) + datetime.timedelta(hours=8)
    return dateStr.date()


def make_query(after_cursor=None):
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


def fetch_releases(oauth_token):
    repos = []
    releases = []
    repo_names = set()
    has_next_page = True
    after_cursor = None

    while has_next_page:
        data = client.execute(
            query=make_query(after_cursor),
            headers={"Authorization": "Bearer {}".format(oauth_token)},
        )

        print(data)

        for repo in data["data"]["viewer"]["repositories"]["nodes"]:
            if repo["releases"]["totalCount"] and repo["name"] not in repo_names:
                releases_nodes = repo["releases"]["nodes"]
                filtered_nodes = [
                    node for node in releases_nodes if node["publishedAt"]]
                if filtered_nodes:
                    latest_release = filtered_nodes[-1]
                    repos.append(repo)
                    repo_names.add(repo["name"])
                    releases.append(
                        {
                            "repo": repo["name"],
                            "repo_url": repo["url"],
                            "description": repo["description"],
                            "release": latest_release["name"].replace(repo["name"], "").strip(),
                            "published_at": latest_release["publishedAt"].split("T")[0],
                            "url": latest_release["url"],
                        }
                    )

        has_next_page = data["data"]["viewer"]["repositories"]["pageInfo"]["hasNextPage"]
        after_cursor = data["data"]["viewer"]["repositories"]["pageInfo"]["endCursor"]

    print(releases)

    return releases


def fetch_douban():
    entries = feedparser.parse(
        "https://www.douban.com/feed/people/kaaaaai/interests")["entries"]
    return [
        {
            "title": item["title"],
            "url": item["link"].split("#")[0],
            "published": formatGMTime(item["published"])
        }
        for item in entries
    ]


def fetch_blog_entries():
    entries = feedparser.parse("https://kaaaaai.cn/atom.xml")["entries"]
    return [
        {
            "title": entry["title"],
            "url": entry["link"].split("#")[0],
            "published": entry["published"].split("T")[0],
        }
        for entry in entries
    ]


def fetch_memos():
    entries = httpx.get(
        "https://memos.kaaaaai.cn/api/v1/memo?openId=bff14007-bcff-4dc2-80ff-5ab9fd61170f")
    print(entries.json())


if __name__ == "__main__":
    inputfile = sys.argv[1]
    readme = root.joinpath(inputfile)
    print(readme.as_uri())
    project_releases = root / "releases.md"

    releases = fetch_releases(GITHUB_TOKEN)
    releases.sort(key=lambda r: r["published_at"], reverse=True)
    md = "\n".join(
        [
            "- [{repo}]({url})：{release}".format(**release)
            for release in releases[:10]
        ]
    )
    readme_contents = readme.open().read()
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

    readme.open("w").write(rewritten)
