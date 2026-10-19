import json
import os
import re
import time
import calendar
import datetime
import feedparser
import requests
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-3.8-flash"

token = os.environ["TELEGRAM_BOT_TOKEN"]
chat_id = os.environ["TELEGRAM_CHAT_ID"]


def call_gemini(prompt):
    """Up to 6 attempts with 10 / 30 / 60 / 120 / 240 s back-off.
    Only retries on 429/500/502/503/504; raises immediately on all other errors."""
    delays = [10, 30, 60, 120, 240]
    retryable = {429, 500, 502, 503, 504}
    for attempt in range(6):
        try:
            return client.models.generate_content(model=MODEL, contents=prompt)
        except Exception as exc:
            code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
            if code is not None and code not in retryable:
                print(f"call_gemini error (not retrying): {exc}")
                raise
            print(f"call_gemini attempt {attempt + 1} failed ({code}): {exc}")
            if attempt < 5:
                time.sleep(delays[attempt])
            else:
                raise


try:
    here = os.path.dirname(__file__)

    sent_path = os.path.join(here, "sent.json")
    if os.path.exists(sent_path):
        sent_links = json.load(open(sent_path))
    else:
        sent_links = {}
    today = datetime.date.today()
    cutoff_date = today - datetime.timedelta(days=14)
    sent_links = {url: date for url, date in sent_links.items()
                  if datetime.date.fromisoformat(date) >= cutoff_date}

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
    before_filter = len(all_stories)
    all_stories = [s for s in all_stories if s["_url"] not in sent_links]
    print(f"Skipped {before_filter - len(all_stories)} already-sent stories")

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

    def _try_parse_pick(response_text):
        raw = response_text.strip()
        if not raw:
            raise ValueError("empty response from Gemini")
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            print(f"Pass 1 JSON parse failed. Raw response:\n{raw}")
            m = re.search(r'\[.*?\]', raw, re.DOTALL)
            if m:
                return json.loads(m.group())
            raise ValueError("no [...] found in pass 1 response")

    picked = None
    for attempt in range(2):
        response_text = call_gemini(pick_prompt).text
        try:
            picked = _try_parse_pick(response_text)
            break
        except Exception as e:
            if attempt == 0:
                print(f"Pass 1 attempt 1 failed ({e}), retrying...")
            else:
                raise RuntimeError(f"Pass 1 failed on both attempts: {e}")
    chosen_indexes = [n - 1 for n in picked]

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
    for i, (s, text) in enumerate(zip(chosen, article_texts), 1):
        reading_parts.append(f"Story {i}: {s['title']}\n{text}")
    reading = "\n\n".join(reading_parts)
    link_instructions = (
        "\n\nFor each story in your digest, end it with exactly "
        "\"Full story: [LINK n]\" where n is that story's number. "
        "Never write any URL yourself."
    )
    prompt = f"{soul}\nAlready taught: (none yet)\nToday's reading:\n{reading}{link_instructions}"

    digest = call_gemini(prompt).text

    link_map = {f"[LINK {i}]": s["_url"] for i, s in enumerate(chosen, 1)}
    for placeholder, url in link_map.items():
        digest = digest.replace(placeholder, url)
    unreplaced = re.findall(r'\[LINK \d+\]', digest)
    for p in unreplaced:
        print(f"WARNING: {p} was not replaced — no matching story URL found")

    if os.environ.get("GITHUB_EVENT_NAME") == "schedule":
        ist_offset = datetime.timedelta(hours=5, minutes=30)
        now_ist = datetime.datetime.utcnow() + ist_offset
        target_ist = now_ist.replace(hour=7, minute=0, second=0, microsecond=0)
        if now_ist < target_ist:
            wait_seconds = (target_ist - now_ist).total_seconds()
            print(f"Joe waiting {wait_seconds:.0f}s until 7:00am IST...")
            time.sleep(wait_seconds)

    tg_url = f"https://api.telegram.org/bot{token}/sendMessage"
    pieces = [p.strip() for p in digest.split("---") if p.strip()]
    hype_words = ["busy", "huge", "significant", "major", "crazy", "massive", "exciting", "game-changer", "revolutionary"]
    if pieces:
        triggered = next((w for w in hype_words if w in pieces[0].lower()), None)
        if triggered:
            story_count = len(pieces) - 1
            pieces[0] = f"Morning Vaanya. {story_count} stories today."
            print(f"Greeting replaced — triggered by: '{triggered}'")
    for piece in pieces:
        response = requests.post(tg_url, json={"chat_id": chat_id, "text": piece})
        print(response.status_code, response.text)
    today_str = today.isoformat()
    for s in chosen:
        sent_links[s["_url"]] = today_str
    with open(sent_path, "w") as f:
        json.dump(sent_links, f, indent=2)
except Exception as exc:
    tg_url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(tg_url, json={"chat_id": chat_id, "text": "Joe couldn't finish this morning's digest: " + str(exc)[:300]})
    raise
