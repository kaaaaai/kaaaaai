# coding: utf-8
from bs4 import BeautifulSoup
import requests
import time
import os

from dotenv import load_dotenv


load_dotenv(verbose=True)

memos_token = os.environ.get("MEMOS_TOKEN", "")

"""
https://github.com/zkeq/news/blob/main/api/crawler.py
"""


def get_zhihu_days(index):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.66 Safari/537.36 Edg/103.0.1264.44"
    }
    base_url = f"https://www.zhihu.com/api/v4/columns/c_1261258401923026944/items?limit=1&offset={index}"
    data = requests.get(base_url, headers=headers).json()
    html = data['data'][0]['content']
    day_news = BeautifulSoup(html, 'lxml').find_all('p')

    final_list = []
    for i in day_news:
        i = i.text
        if i != '':
            final_list.append(i)
    final_list[0], final_list[1] = final_list[1], final_list[0]
    return final_list, base_url


def get_163_days(index):
    list_url = 'https://www.163.com/dy/media/T1603594732083.html'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.66 Safari/537.36 Edg/103.0.1264.44",
        "realIP": "218.109.147.57"
    }

    data = requests.get(list_url, headers=headers)
    soup = BeautifulSoup(data.text, 'lxml')
    new_url = soup.find_all('a', attrs={"class": "title"})[index]['href']
    new_data = requests.get(new_url, headers=headers)
    soup = BeautifulSoup(new_data.text, 'lxml')
    day_news = soup.find('div', attrs={"class": "post_body"})
    list_all = str(day_news).split('<br/>')

    final_list = []
    for i in list_all:
        if "↑" in i:
            continue
        if "<" not in i and ">" not in i and i != '':
            i.replace('\u200b', '')
            final_list.append(i)
    return final_list, new_url


def main(index, origin):
    if origin == 'zhihu':
        try:
            data, new_url = get_zhihu_days(index)
            suc = True
        except Exception as e:
            data = [str(e)] * 18
            suc = False
    else:
        try:
            data, new_url = get_163_days(index)
            suc = True
        except Exception as e:
            data = [str(e)] * 18
            suc = False
    
    return {
        'suc': suc,
        'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        'data': {
            'title': data[0],
            'date': data[1],
            'news': data[2:-1],
            'weiyu': data[-1],
            'all_data': data,
            'source_url': new_url
        }
    }


news = main(0, '163')

all_data = news["data"]['all_data']
all_data.append("新闻来源：" + news["data"]['source_url'])

all_data.append("#每日早报 #memos")
message = '\n\n'.join(all_data)

print(message)

url = f'https://memos.chensoul.cc/api/v1/memo'
payload = {
    "content": message
}
headers = {
    "Content-Type": "application/json; charset=utf-8",
    "Authorization": f'Bearer {memos_token}'
}

# response = requests.post(url, json=payload, headers=headers)
# print(response)
