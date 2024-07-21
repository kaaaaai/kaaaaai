import csv
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

import requests


load_dotenv(verbose=True)

wakatime_token = os.environ.get("WAKATIME_TOKEN", "")
memos_token = os.environ.get("MEMOS_TOKEN", "")

print(wakatime_token)
print(memos_token)


def save_history():
    # 读取 JSON 文件
    with open('wakatime.json') as f:
        days = json.load(f)["days"]
        recent_data = [
            [d["date"], round(d["grand_total"]["total_seconds"])] for d in days]

    print(recent_data)

    # 将数据写入 CSV 文件
    with open('data/coding.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(recent_data)


def save_yesterday():
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    url = f'https://wakatime.com/api/v1/users/current/summaries?api_key={wakatime_token}&start={yesterday}&end={yesterday}'

    response = requests.get(url)

    if response.status_code == 200:
        result = json.loads(response.text)

        day = result['start']
        cost = round(result['cumulative_total']['seconds'])
        cost_text = result['cumulative_total']['text'].replace(
            "hrs", "小时").replace("mins", "分钟")

        date = datetime.strptime(
            day, '%Y-%m-%dT%H:%M:%SZ') + timedelta(hours=8)
        normal_date = date.strftime('%Y-%m-%d')

        if cost > 0:
            china_date_str = date.strftime('%Y年%m月%d日')
            memos_data = {
                "content": f"{china_date_str}，今天写代码花了 {cost_text} #wakatime"}
            json_data = json.dumps(memos_data)

            requests.post(f'https://memos.kaaaaai.cn/api/v1/memos',
                          data=json_data, headers={'Content-Type': 'application/json', "Authorization": f'Bearer {memos_token}'})

        # 将数据写入 CSV 文件
        with open('data/coding.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerows([[normal_date, cost]])
    else:
        print(response.text)


save_yesterday()
