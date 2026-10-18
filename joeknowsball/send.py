import json
import os
import re
import time
import calendar
import feedparser
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


here = os.path.dirname(__file__)

top_ids = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json").json()[:30]
hn_stories = [requests.get(f"https://hacker-news.firebaseio.com/v0/item/{id}.json").json() for id in top_ids]
for s in hn_stories:
    s["_url"] = s.get("url", f"https://news.ycombinator.com/item?id={s['id']}")

cutoff = time.time() - 259200
feed_stories = []
feed_urls = [l.strip() for l in open(os.path.join(here, "sources.txt")) if l.strip() and not l.startswith("#")]
for feed_url in feed_urls:
    feed = feedparser.parse(feed_url)
    fresh = []
    for e in feed.entries:
        t = e.get("published_parsed") or e.get("updated_parsed")
        if t and calendar.timegm(t) >= cutoff:
            snippet = re.sub(r"<[^>]+>", "", e.get("summary", ""))[:300]
            fresh.append({"title": e.title, "_url": e.link, "_source": feed.feed.title, "_snippet": snippet})
    print(feed.feed.get("title", feed_url), len(fresh), "fresh entries")
    feed_stories.extend(fresh)

soul = open(os.path.join(here, "SOUL.md")).read()

all_stories = hn_stories + feed_stories

def story_label(s):
    if "_source" in s:
        return f"(from {s['_source']})"
    return f"({s.get('score', 0)} points, {s.get('descendants', 0)} comments)"

def story_line(i, s):
    line = f"{i+1}. {s['title']} {story_label(s)}"
    if "_snippet" in s and s["_snippet"]:
        line += f"\n   {s['_snippet']}"
    return line

numbered = "\n".join(story_line(i, s) for i, s in enumerate(all_stories))
n = len(all_stories)
pick_prompt = (
    f"{soul}\n\nHere are today's {n} stories:\n{numbered}\n\n"
    f"Return ONLY a JSON array of the numbers (1-{n}) of up to 7 stories worth covering today, "
    "most important first. Return [] if none qualify."
)

raw = call_gemini(pick_prompt).text.strip()
if raw.startswith("```"):
    raw = raw.split("```")[1]
    if raw.startswith("json"):
        raw = raw[4:]
    raw = raw.strip()
chosen_indexes = [n - 1 for n in json.loads(raw)]

if not chosen_indexes:
    tg_url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(tg_url, json={"chat_id": chat_id, "text": "Good morning Vaanya. Nothing worth your time today."})
    print("Nothing to send today.")
    exit()

chosen = [all_stories[i] for i in chosen_indexes]
for s in chosen:
    print(s["title"])

article_texts = []
for s in chosen:
    text = requests.get("https://r.jina.ai/" + s["_url"], timeout=30).text[:15000]
    print(s["_url"], len(text), "chars")
    article_texts.append(text)

reading_parts = []
for s, text in zip(chosen, article_texts):
    reading_parts.append(f"{s['title']}\n{s['_url']}\n{text}")
reading = "\n\n".join(reading_parts)
prompt = f"{soul}\nAlready taught: (none yet)\nToday's reading:\n{reading}"

digest = call_gemini(prompt).text

tg_url = f"https://api.telegram.org/bot{token}/sendMessage"
for piece in digest.split("---"):
    piece = piece.strip()
    if not piece:
        continue
    response = requests.post(tg_url, json={"chat_id": chat_id, "text": piece})
    print(response.status_code, response.text)
