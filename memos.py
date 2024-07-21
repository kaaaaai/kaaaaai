from datetime import datetime, timedelta
import sys
import requests
from dotenv import load_dotenv
import os

load_dotenv()
memos_token = os.getenv('MEMOS_TOKEN')

url = f'https://memos.kaaaaai.cn/api/v1/memo'


def create_diary():
    today = datetime.now().date()
    year = today.year
    month = today.month
    message = f'''#日记/{year}/{month} {today.strftime("%Y年%m月%d日")}

**习惯**
- [ ] 喝水

**今天做了什么**
1. 

**今天收获了什么**
    '''

    payload = {
        "content": message
    }
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f'Bearer {memos_token}'
    }

    response = requests.post(url, json=payload, headers=headers)
    print(response.text)


def create_weekly():
    today = datetime.now().date()
    year = today.year
    week_number = int(today.strftime("%W")) + 1

    last_monday = today - timedelta(days=today.weekday(), weeks=1)
    last_sunday = last_monday + timedelta(days=6)

    message = f'''#周报/{year} 周报{week_number}｜{last_monday} ~ {last_sunday}

**本周收获**

**下周计划**
    '''

    payload = {
        "content": message
    }
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f'Bearer {memos_token}'
    }

    response = requests.post(url, json=payload, headers=headers)
    print(response.text)


if __name__ == "__main__":
    arg = sys.argv[1]
    if arg == 'diary':
        create_diary()
    else:
        create_weekly()
