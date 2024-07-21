import requests
from dotenv import load_dotenv
import os

load_dotenv()
pinboard_api_key = os.getenv('pinboard_api_key')
memos_token = os.getenv('MEMOS_TOKEN')

memos_endpoint = 'https://memos.kaaaaai.cn/api/v1/memo'

def fetch_pinboard_data():
    url = 'https://api.pinboard.in/v1/posts/all'
    params = {
        'auth_token': pinboard_api_key,
        'format': 'json'
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f'Failed to fetch Pinboard data. Status code: {response.status_code}')
        return None


def post_memo(memo):
    payload = {
        "content": memo
    }
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f'Bearer {memos_token}'
    }
    response = requests.post(memos_endpoint, json=payload, headers=headers)
    if response.status_code == 200:
        print('Memo posted successfully.')
    else:
        print(f'Failed to post memo. Status code: {response.status_code}')

def main():
    pinboard_data = fetch_pinboard_data()
    if pinboard_data:
        sorted_data = sorted(pinboard_data, key=lambda x: x['time'])
        for item in sorted_data:
            title = item['description']
            url = item['href']
            tags = item['tags'].split(' ')
            tags = [tag for tag in tags if tag]  # 过滤掉空字符串
            if tags:
                tags = ' '.join([f'#bookmark/{tag}' for tag in tags])
            else:  
                tags = '#bookmark'
            memo = f'{title} \n{url} \n{tags}'
            print(memo)
            post_memo(memo)

if __name__ == '__main__':
    main()