import requests
import json

import asyncio

import os
from dotenv import load_dotenv

load_dotenv()
PASS = os.getenv("NOTIFY_PASS")
# URL твоего сервера FastAPI
SERVER_URL = "https://likhtarychok.org/"


def send_notification(message: str, title: str):
    """
    Отправляет уведомление всем подписанным клиентам через /notify
    """
    data = {"message": message, "title": title, "pass": PASS}
    response = requests.post(
        f"{SERVER_URL}/notify",
        headers={"Content-Type": "application/json"},
        data=json.dumps(data)
    )

    if response.status_code == 200:
        res = response.json()
        print(f"✅ Уведомление отправлено {res.get('sent', 0)} клиентам. \n{res.get('msg', '')}")
    else:
        print(f"❌ Ошибка {response.status_code}: {response.text}")

async def start():
    while True:
        msg = input("Текст уведомления: ").strip()
        title = input("Заголовок: ").strip()
        if msg and title:
            send_notification(msg, title)
        else:
            print("⚠️ Сообщение не может быть пустым.")
        

        # await asyncio.sleep(3)
        # os.system("cls")


if __name__ == "__main__":
    asyncio.run(start())