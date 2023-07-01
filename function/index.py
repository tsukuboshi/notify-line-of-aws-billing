import boto3
import os
import urllib
import json
from datetime import datetime, timedelta, date
from typing import Tuple

import logging

client = boto3.client('ce', region_name='us-east-1')


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context) -> None:
    try:
        # LINEアクセストークンを取得する
        token = get_access_token()

        # 合計とサービス毎の請求額を取得する
        total_billing = get_total_billing(client)
        service_billings = get_service_billings(client)
        title, detail = get_message(total_billing, service_billings)

        # Line用のメッセージを作成して投げる
        post_line(title, detail, token)

    except Exception as e:
        logger.exception("Exception occurred: %s", e)
        raise e


def get_access_token() -> str:
    line_access_token_path = os.environ['ACCESS_TOKEN_PATH']
    print("Loading AWS Systems Manager Parameter Store values from " + line_access_token_path)
    req = urllib.request.Request('http://localhost:2773/systemsmanager/parameters/get/?name=' + line_access_token_path + '&withDecryption=true')
    req.add_header('X-Aws-Parameters-Secrets-Token', os.environ.get('AWS_SESSION_TOKEN'))
    config = urllib.request.urlopen(req).read()
    access_token = json.loads(config.decode("utf-8"))['Parameter']['Value']
    return access_token


def get_total_billing(client) -> dict:
    (start_date, end_date) = get_total_cost_date_range()

    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ce.html#CostExplorer.Client.get_cost_and_usage
    response = client.get_cost_and_usage(
        TimePeriod={
            'Start': start_date,
            'End': end_date
        },
        Granularity='MONTHLY',
        Metrics=[
            'AmortizedCost'
        ]
    )
    return {
        'start': response['ResultsByTime'][0]['TimePeriod']['Start'],
        'end': response['ResultsByTime'][0]['TimePeriod']['End'],
        'billing': response['ResultsByTime'][0]['Total']['AmortizedCost']['Amount'],
    }


def get_service_billings(client) -> list:
    (start_date, end_date) = get_total_cost_date_range()

    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ce.html#CostExplorer.Client.get_cost_and_usage
    response = client.get_cost_and_usage(
        TimePeriod={
            'Start': start_date,
            'End': end_date
        },
        Granularity='MONTHLY',
        Metrics=[
            'AmortizedCost'
        ],
        GroupBy=[
            {
                'Type': 'DIMENSION',
                'Key': 'SERVICE'
            }
        ]
    )

    billings = []

    for item in response['ResultsByTime'][0]['Groups']:
        billings.append({
            'service_name': item['Keys'][0],
            'billing': item['Metrics']['AmortizedCost']['Amount']
        })
    return billings


def get_message(total_billing: dict, service_billings: list) -> Tuple[str, str]:
    start = datetime.strptime(total_billing['start'], '%Y-%m-%d').strftime('%m/%d')

    # Endの日付は結果に含まないため、表示上は前日にしておく
    end_today = datetime.strptime(total_billing['end'], '%Y-%m-%d')
    end_yesterday = (end_today - timedelta(days=1)).strftime('%m/%d')

    total = round(float(total_billing['billing']), 2)

    title = f'{start}～{end_yesterday}の請求額は、{total:.2f} USDです。'

    details = []
    for item in service_billings:
        service_name = item['service_name']
        billing = round(float(item['billing']), 2)

        if billing == 0.0:
            # 請求無し（0.0 USD）の場合は、内訳を表示しない
            continue
        details.append(f'　・{service_name}: {billing:.2f} USD')

    return title, '\n'.join(details)


def post_line(title: str, detail: str, token: str) -> None:
    # https://notify-bot.line.me/doc/ja/
    print("Accessing Line Notify")
    url = "https://notify-api.line.me/api/notify"
    # headers = {"Authorization": "Bearer %s" % LINE_ACCESS_TOKEN}
    headers = {"Authorization": "Bearer %s" % token}
    payload = {"message": f"{title}\n\n{detail}"}
    data = urllib.parse.urlencode(payload).encode("utf-8")

    request = urllib.request.Request(url=url, data=data, method="POST", headers=headers)
    urllib.request.urlopen(request)


def get_total_cost_date_range() -> Tuple[str, str]:
    start_date = get_begin_of_month()
    end_date = get_today()

    # get_cost_and_usage()のstartとendに同じ日付は指定不可のため、
    # 「今日が1日」なら、「先月1日から今月1日（今日）」までの範囲にする
    if start_date == end_date:
        end_of_month = datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=-1)
        begin_of_month = end_of_month.replace(day=1)
        return begin_of_month.date().isoformat(), end_date
    return start_date, end_date


def get_begin_of_month() -> str:
    return date.today().replace(day=1).isoformat()


def get_prev_day(prev: int) -> str:
    return (date.today() - timedelta(days=prev)).isoformat()


def get_today() -> str:
    return date.today().isoformat()
