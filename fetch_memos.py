import requests
import json
import time
import csv
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()
memos_token = os.getenv('MEMOS_TOKEN')

url = f'https://memos.kaaaaai.cn/api/v1/memos'

keyword = '#日记'

# 计算上周一和上周日的日期
today = datetime.now().date()
last_monday = today - timedelta(days=today.weekday(), weeks=1)
last_sunday = last_monday + timedelta(days=6)

# 将日期转换为秒
start_time = int(time.mktime(today.timetuple()))

response = requests.get(url, headers={
                        'Content-Type': 'application/json', "Authorization": f'Bearer {memos_token}'})

if response.status_code == 200:
    data = json.loads(response.text)
    recent_data = data
    # recent_data = [d for d in data if start_time <= d['createdTs']]

    with open('data/memos.csv', 'w', newline=''):
        pass

    with open('data/memos.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['day', 'time', 'url', 'content'])

    memos = data['memos']

    # 将数据转换为 Markdown 格式，并处理 URL
    for d in memos:
        # if keyword in content:
        created_time = datetime.fromisoformat(d['createTime'].rstrip('Z'))
        date_str = '{}'.format(created_time.strftime('%Y-%m-%d'))
        time_str = '{}'.format(created_time.strftime('%H:%M:%S'))

        content = d['content']
        content = content.split('\n')[0].replace(',', '，').replace('**', '')
        # content = content.replace('\n', "")

        url = 'https://memos.kaaaaai.cn/m/{} '.format(d['uid'])

        # 将数据写入 CSV 文件
        with open('data/memos.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerows([[date_str, time_str, url, content]])
else:
    print('请求失败：', response.status_code)
