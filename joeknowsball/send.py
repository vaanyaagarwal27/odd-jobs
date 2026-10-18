import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.environ["TELEGRAM_BOT_TOKEN"]
chat_id = os.environ["TELEGRAM_CHAT_ID"]

url = f"https://api.telegram.org/bot{token}/sendMessage"
response = requests.post(url, json={"chat_id": chat_id, "text": "good morning — joe is alive"})
print(response.status_code)
