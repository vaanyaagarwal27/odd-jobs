import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.environ["TELEGRAM_BOT_TOKEN"]
chat_id = os.environ["TELEGRAM_CHAT_ID"]

top_ids = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json").json()[:5]
stories = [requests.get(f"https://hacker-news.firebaseio.com/v0/item/{id}.json").json() for id in top_ids]

lines = ["top on hacker news today"]
for i, s in enumerate(stories, 1):
    lines.append(f"{i}. {s['title']}")
    lines.append(s.get("url", f"https://news.ycombinator.com/item?id={s['id']}"))

url = f"https://api.telegram.org/bot{token}/sendMessage"
response = requests.post(url, json={"chat_id": chat_id, "text": "\n".join(lines)})
print(response.status_code)
