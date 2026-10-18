import os
import time
import requests
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.5-flash"

token = os.environ["TELEGRAM_BOT_TOKEN"]
chat_id = os.environ["TELEGRAM_CHAT_ID"]


def call_gemini(prompt):
    """Up to 3 retries with 2 / 4 / 8 s back-off; re-raises on final failure."""
    delays = [2, 4, 8]
    for attempt in range(4):
        try:
            return client.models.generate_content(model=MODEL, contents=prompt)
        except Exception as exc:
            if attempt < 3:
                time.sleep(delays[attempt])
            else:
                raise exc


top_ids = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json").json()[:30]
stories = [requests.get(f"https://hacker-news.firebaseio.com/v0/item/{id}.json").json() for id in top_ids]

soul = open(os.path.join(os.path.dirname(__file__), "SOUL.md")).read()

story_parts = []
for s in stories:
    hn_url = f"https://news.ycombinator.com/item?id={s['id']}"
    story_parts.append(f"{s['title']} {s.get('url', hn_url)}")
story_lines = "\n".join(story_parts)
prompt = f"{soul}\nAlready taught: (none yet)\nToday's reading:\n{story_lines}"

digest = call_gemini(prompt).text

url = f"https://api.telegram.org/bot{token}/sendMessage"
for piece in digest.split("---"):
    piece = piece.strip()
    if not piece:
        continue
    response = requests.post(url, json={"chat_id": chat_id, "text": piece})
    print(response.status_code, response.text)